from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncGenerator, Generator, Optional, Union, Tuple, List
import pyodbc
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint import BaseCheckpointSaver
from langgraph.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.base import Checkpoint, CheckpointMetadata, CheckpointTuple

class MSSQLSaver(BaseCheckpointSaver):
    connection_string: str
    """The connection string for the MS SQL Server database."""

    def __init__(self, connection_string: str):
        super().__init__(serde=JsonPlusSerializer())
        self.connection_string = connection_string

    @contextmanager
    def _get_connection(self) -> Generator[pyodbc.Connection, None, None]:
        """Get the connection to the MS SQL Server database."""
        conn = pyodbc.connect(self.connection_string)
        try:
            yield conn
        finally:
            conn.close()

    CREATE_TABLES_QUERY = """
    IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[checkpoints]') AND type in (N'U'))
    BEGIN
    CREATE TABLE checkpoints (
        thread_id NVARCHAR(255) NOT NULL,
        thread_ts NVARCHAR(255) NOT NULL,
        parent_ts NVARCHAR(255),
        checkpoint VARBINARY(MAX) NOT NULL,
        metadata VARBINARY(MAX) NOT NULL,
        PRIMARY KEY (thread_id, thread_ts)
    )
    END
    """

    def create_tables(self):
        """Create the schema for the checkpoint saver."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(self.CREATE_TABLES_QUERY)
            conn.commit()

    UPSERT_CHECKPOINT_QUERY = """
    MERGE INTO checkpoints AS target
    USING (VALUES (?, ?, ?, ?, ?)) AS source (thread_id, thread_ts, parent_ts, checkpoint, metadata)
    ON (target.thread_id = source.thread_id AND target.thread_ts = source.thread_ts)
    WHEN MATCHED THEN
        UPDATE SET checkpoint = source.checkpoint, metadata = source.metadata
    WHEN NOT MATCHED THEN
        INSERT (thread_id, thread_ts, parent_ts, checkpoint, metadata)
        VALUES (source.thread_id, source.thread_ts, source.parent_ts, source.checkpoint, source.metadata);
    """

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
    ) -> RunnableConfig:
        thread_id = config["configurable"]["thread_id"]
        parent_ts = config["configurable"].get("thread_ts")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                self.UPSERT_CHECKPOINT_QUERY,
                (
                    thread_id,
                    checkpoint["ts"],
                    parent_ts if parent_ts else None,
                    self.serde.dumps(checkpoint),
                    self.serde.dumps(metadata),
                ),
            )
            conn.commit()

        return {
            "configurable": {
                "thread_id": thread_id,
                "thread_ts": checkpoint["ts"],
            },
        }

    LIST_CHECKPOINTS_QUERY_STR = """
    SELECT checkpoint, metadata, thread_ts, parent_ts
    FROM checkpoints
    {where}
    ORDER BY thread_ts DESC
    """

    def list(
        self,
        config: Optional[RunnableConfig],
        *,
        filter: Optional[dict[str, Any]] = None,
        before: Optional[RunnableConfig] = None,
        limit: Optional[int] = None,
    ) -> Generator[CheckpointTuple, None, None]:
        where, args = self._search_where(config, filter, before)
        query = self.LIST_CHECKPOINTS_QUERY_STR.format(where=where)
        if limit:
            query += f" OFFSET 0 ROWS FETCH NEXT {limit} ROWS ONLY"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            thread_id = config["configurable"]["thread_id"]
            cursor.execute(query, tuple(args))
            for value in cursor.fetchall():
                checkpoint, metadata, thread_ts, parent_ts = value
                yield CheckpointTuple(
                    config={
                        "configurable": {
                            "thread_id": thread_id,
                            "thread_ts": thread_ts,
                        }
                    },
                    checkpoint=self.serde.loads(checkpoint),
                    metadata=self.serde.loads(metadata),
                    parent_config={
                        "configurable": {
                            "thread_id": thread_id,
                            "thread_ts": thread_ts,
                        }
                    }
                    if parent_ts
                    else None,
                )

    GET_CHECKPOINT_BY_TS_QUERY = """
    SELECT checkpoint, metadata, thread_ts, parent_ts
    FROM checkpoints
    WHERE thread_id = ? AND thread_ts = ?
    """

    GET_CHECKPOINT_QUERY = """
    SELECT TOP 1 checkpoint, metadata, thread_ts, parent_ts
    FROM checkpoints
    WHERE thread_id = ?
    ORDER BY thread_ts DESC
    """

    def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        thread_id = config["configurable"]["thread_id"]
        thread_ts = config["configurable"].get("thread_ts")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if thread_ts:
                cursor.execute(
                    self.GET_CHECKPOINT_BY_TS_QUERY,
                    (thread_id, thread_ts),
                )
                value = cursor.fetchone()
                if value:
                    checkpoint, metadata, thread_ts, parent_ts = value
                return CheckpointTuple(
                    config=config,
                    checkpoint=self.serde.loads(checkpoint),
                    metadata=self.serde.loads(metadata),
                    parent_config={
                        "configurable": {
                            "thread_id": thread_id,
                            "thread_ts": thread_ts,
                        }
                    }
                    if thread_ts
                    else None,
                )
            else:
                cursor.execute(
                    self.GET_CHECKPOINT_QUERY,
                    (thread_id,),
                )
                value = cursor.fetchone()
                if value:
                    checkpoint, metadata, thread_ts, parent_ts = value
                    return CheckpointTuple(
                        config={
                            "configurable": {
                                "thread_id": thread_id,
                                "thread_ts": thread_ts,
                            }
                        },
                        checkpoint=self.serde.loads(checkpoint),
                        metadata=self.serde.loads(metadata),
                        parent_config={
                            "configurable": {
                                "thread_id": thread_id,
                                "thread_ts": parent_ts,
                            }
                        }
                        if parent_ts
                        else None,
                    )
        return None

    def _search_where(
        self,
        config: Optional[RunnableConfig],
        filter: Optional[dict[str, Any]] = None,
        before: Optional[RunnableConfig] = None,
    ) -> Tuple[str, List[Any]]:
        wheres = []
        param_values = []

        if config is not None:
            wheres.append("thread_id = ?")
            param_values.append(config["configurable"]["thread_id"])

        if filter:
            raise NotImplementedError()

        if before is not None:
            wheres.append("thread_ts < ?")
            param_values.append(before["configurable"]["thread_ts"])

        where_clause = "WHERE " + " AND ".join(wheres) if wheres else ""
        return where_clause, param_values