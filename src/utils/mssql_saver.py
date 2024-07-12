import pyodbc
from typing import Optional, Iterator, Dict, Any, Tuple, Sequence
from contextlib import contextmanager
from langgraph.checkpoint.base import BaseCheckpointSaver, CheckpointTuple, Checkpoint
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite import JsonPlusSerializerCompat
import threading
from hashlib import md5
import json
import pickle
import sqlite3
import threading
from contextlib import AbstractContextManager, contextmanager
from hashlib import md5
from types import TracebackType
from typing import Any, AsyncIterator, Dict, Iterator, Optional, Sequence, Tuple, List

from langchain_core.runnables import RunnableConfig
from typing_extensions import Self
from langgraph.errors import EmptyChannelError

from langgraph.channels.base import BaseChannel
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    SerializerProtocol,
)

class MSSQLSaver(BaseCheckpointSaver):
    """A checkpoint saver that stores checkpoints in a Microsoft SQL Server database."""

    serde = JsonPlusSerializerCompat()

    def __init__(
        self,
        conn_string: str,
        *,
        serde: Optional[SerializerProtocol] = None,
    ) -> None:
        super().__init__(serde=serde)
        self.conn_string = conn_string
        self.is_setup = False
        self.lock = threading.Lock()

    @contextmanager
    def connection(self):
        conn = pyodbc.connect(self.conn_string)
        try:
            yield conn
        finally:
            conn.close()

    def setup(self) -> None:
        if self.is_setup:
            return

        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'checkpoints_data')
                CREATE TABLE checkpoints_data (
                    thread_id NVARCHAR(255) NOT NULL,
                    thread_ts NVARCHAR(255) NOT NULL,
                    parent_ts NVARCHAR(255),
                    checkpoint_blob VARBINARY(MAX),
                    metadata VARBINARY(MAX),
                    PRIMARY KEY (thread_id, thread_ts)
                )
            """)
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'writes_data')
                CREATE TABLE writes_data (
                    thread_id NVARCHAR(255) NOT NULL,
                    thread_ts NVARCHAR(255) NOT NULL,
                    task_id NVARCHAR(255) NOT NULL,
                    idx INT NOT NULL,
                    channel NVARCHAR(255) NOT NULL,
                    value VARBINARY(MAX),
                    PRIMARY KEY (thread_id, thread_ts, task_id, idx)
                )
            """)
            conn.commit()

        self.is_setup = True

    def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        self.setup()
        with self.connection() as conn:
            cursor = conn.cursor()
            if config["configurable"].get("thread_ts"):
                cursor.execute(
                    "SELECT thread_id, thread_ts, parent_ts, checkpoint_blob, metadata FROM checkpoints_data WHERE thread_id = ? AND thread_ts = ?",
                    (str(config["configurable"]["thread_id"]), str(config["configurable"]["thread_ts"]))
                )
            else:
                cursor.execute(
                    "SELECT TOP 1 thread_id, thread_ts, parent_ts, checkpoint_blob, metadata FROM checkpoints_data WHERE thread_id = ? ORDER BY thread_ts DESC",
                    (str(config["configurable"]["thread_id"]),)
                )
            
            value = cursor.fetchone()
            if value:
                if not config["configurable"].get("thread_ts"):
                    config = {
                        "configurable": {
                            "thread_id": value[0],
                            "thread_ts": value[1],
                        }
                    }
                
                checkpoint: Dict[str, Any] = self.serde.loads(value[3])
                metadata: Dict[str, Any] = self.serde.loads(value[4]) if value[4] is not None else {}
                
                parent_config = None
                if value[2]:  # if parent_ts is not None
                    parent_config = {
                        "configurable": {
                            "thread_id": value[0],
                            "thread_ts": value[2],
                        }
                    }
                
                return CheckpointTuple(
                    config=config,
                    checkpoint=checkpoint,
                    metadata=metadata,
                    parent_config=parent_config
                )
        return None

    def list(
        self,
        config: Optional[RunnableConfig],
        *,
        filter: Optional[Dict[str, Any]] = None,
        before: Optional[RunnableConfig] = None,
        limit: Optional[int] = None,
    ) -> Iterator[CheckpointTuple]:
        self.setup()
        query = """
            SELECT thread_id, thread_ts, parent_ts, checkpoint_blob, metadata
            FROM checkpoints_data
            WHERE 1=1
        """
        params = []

        if config and config["configurable"].get("thread_id"):
            query += " AND thread_id = ?"
            params.append(str(config["configurable"]["thread_id"]))

        if before and before["configurable"].get("thread_ts"):
            query += " AND thread_ts < ?"
            params.append(str(before["configurable"]["thread_ts"]))

        query += " ORDER BY thread_ts DESC"

        if limit:
            query = f"SELECT TOP {limit} " + query[7:]

        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            for thread_id, thread_ts, parent_ts, checkpoint_blob, metadata in cursor:
                yield CheckpointTuple(
                    {"configurable": {"thread_id": thread_id, "thread_ts": thread_ts}},
                    self.serde.loads(checkpoint_blob),
                    self.serde.loads(metadata) if metadata is not None else {},
                    (
                        {
                            "configurable": {
                                "thread_id": thread_id,
                                "thread_ts": parent_ts,
                            }
                        }
                        if parent_ts
                        else None
                    ),
                )

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: Dict[str, Any],
    ) -> RunnableConfig:
        self.setup()
        with self.lock, self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "MERGE INTO checkpoints_data AS target "
                "USING (VALUES (?, ?, ?, ?, ?)) AS source (thread_id, thread_ts, parent_ts, checkpoint_blob, metadata) "
                "ON target.thread_id = source.thread_id AND target.thread_ts = source.thread_ts "
                "WHEN MATCHED THEN "
                "    UPDATE SET parent_ts = source.parent_ts, checkpoint_blob = source.checkpoint_blob, metadata = source.metadata "
                "WHEN NOT MATCHED THEN "
                "    INSERT (thread_id, thread_ts, parent_ts, checkpoint_blob, metadata) "
                "    VALUES (source.thread_id, source.thread_ts, source.parent_ts, source.checkpoint_blob, source.metadata);",
                (
                    str(config["configurable"]["thread_id"]),
                    checkpoint["id"],
                    config["configurable"].get("thread_ts"),
                    self.serde.dumps(checkpoint),
                    self.serde.dumps(metadata),
                )
            )
            conn.commit()
        return {
            "configurable": {
                "thread_id": config["configurable"]["thread_id"],
                "thread_ts": checkpoint["id"],
            }
        }

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[Tuple[str, Any]],
        task_id: str,
    ) -> None:
        self.setup()
        with self.lock, self.connection() as conn:
            cursor = conn.cursor()
            for idx, (channel, value) in enumerate(writes):
                cursor.execute(
                    "MERGE INTO writes_data AS target "
                    "USING (VALUES (?, ?, ?, ?, ?, ?)) AS source (thread_id, thread_ts, task_id, idx, channel, value) "
                    "ON target.thread_id = source.thread_id AND target.thread_ts = source.thread_ts AND target.task_id = source.task_id AND target.idx = source.idx "
                    "WHEN MATCHED THEN "
                    "    UPDATE SET channel = source.channel, value = source.value "
                    "WHEN NOT MATCHED THEN "
                    "    INSERT (thread_id, thread_ts, task_id, idx, channel, value) "
                    "    VALUES (source.thread_id, source.thread_ts, source.task_id, source.idx, source.channel, source.value);",
                    (
                        str(config["configurable"]["thread_id"]),
                        str(config["configurable"]["thread_ts"]),
                        task_id,
                        idx,
                        channel,
                        self.serde.dumps(value),
                    )
                )
            conn.commit()

    def get_next_version(self, current: Optional[str], channel: Any) -> str:
        if current is None:
            current_v = 0
        else:
            current_v = int(current.split(".")[0])
        next_v = current_v + 1
        try:
            next_h = md5(self.serde.dumps(channel.checkpoint())).hexdigest()
        except EmptyChannelError:
            next_h = ""
        except AttributeError:
            next_h = ""
        return f"{next_v:032}.{next_h}"
    
    def get_conversation_history(self, thread_id: str) -> List[Dict[str, Any]]:
        with self.connection() as conn:
            cursor = conn.cursor()
            query = "SELECT [checkpoint_blob] FROM checkpoints_data WHERE thread_id = ? ORDER BY thread_ts DESC"
            # query = "SELECT [checkpoint_blob] FROM checkpoints_data WHERE thread_id = '700f8466-568b-46b9-986a-63073f13d545' ORDER BY thread_ts DESC"
            cursor.execute(
                query,
                (thread_id,)
            )
            row = cursor.fetchone()
            print(row)
            
            if row and row[0]:
                serialized_data = row[0]
                deserialized_data = self.serde.loads(serialized_data)
                print("deserialized:", deserialized_data)
                
                # Assuming the conversation history is stored in a specific format
                # You might need to adjust this based on your actual data structure
                if isinstance(deserialized_data, dict) and 'conversation_history' in deserialized_data:
                    return deserialized_data['conversation_history']
                elif isinstance(deserialized_data, list):
                    return deserialized_data  # Assuming the entire checkpoint is the conversation history
                else:
                    return []
            else:
                return []
            
    def process_checkpoint(self, thread_id: str) -> Dict[str, Any]:
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT [checkpoint_blob] FROM checkpoints_data WHERE thread_id = ? ORDER BY thread_ts DESC",
                (thread_id,)
            )
            row = cursor.fetchone()
            
            if row and row[0]:
                try:
                    deserialized_data = self.serde.loads(row[0])
                    if isinstance(deserialized_data, dict):
                        return deserialized_data
                    else:
                        return {"checkpoint_data": deserialized_data}
                except Exception as e:
                    print(f"Error deserializing checkpoint data: {e}")
                    return {}
            else:
                return {}
            
    def reset_table(self) -> None:
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS checkpoints_data")
            cursor.execute("""
                CREATE TABLE checkpoints_data (
                    thread_id NVARCHAR(255) NOT NULL,
                    thread_ts NVARCHAR(255) NOT NULL,
                    parent_ts NVARCHAR(255),
                    checkpoint_blob VARBINARY(MAX),
                    metadata VARBINARY(MAX),
                    PRIMARY KEY (thread_id, thread_ts)
                )
            """)
            conn.commit()
        self.is_setup = True
        print("checkpoints_data table has been recreated.")