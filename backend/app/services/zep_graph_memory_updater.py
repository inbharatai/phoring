"""
Zep graph memory update service.
Converts simulation agent activities into Zep graph updates.
"""

import time
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from queue import Queue, Empty

from..config import Config
from..utils.logger import get_logger

logger = get_logger('phoring.zep_graph_memory_updater')


@dataclass
class AgentActivity:
    """Agent activity record."""
    platform: str # twitter / reddit
    agent_id: int
    agent_name: str
    action_type: str # CREATE_POST, LIKE_POST, etc.
    action_args: Dict[str, Any]
    round_num: int
    timestamp: str
    
    def to_episode_text(self) -> str:
        """
        Convert activity to a Zep-compatible text description.

        Uses a natural-language description format so Zep can extract entities and relations.
        Adds simulation context to avoid ambiguous graph updates.
        """
        # Generate description based on action type
        action_descriptions = {
            "CREATE_POST": self._describe_create_post,
            "LIKE_POST": self._describe_like_post,
            "DISLIKE_POST": self._describe_dislike_post,
            "REPOST": self._describe_repost,
            "QUOTE_POST": self._describe_quote_post,
            "FOLLOW": self._describe_follow,
            "CREATE_COMMENT": self._describe_create_comment,
            "LIKE_COMMENT": self._describe_like_comment,
            "DISLIKE_COMMENT": self._describe_dislike_comment,
            "SEARCH_POSTS": self._describe_search,
            "SEARCH_USER": self._describe_search_user,
            "MUTE": self._describe_mute,
        }
        
        describe_func = action_descriptions.get(self.action_type, self._describe_generic)
        description = describe_func()
        
        # Return "agent: description" format with simulation context
        return f"{self.agent_name}: {description}"
    
    def _describe_create_post(self) -> str:
        content = self.action_args.get("content", "")
        if content:
            return f"publish post: '{content}'"
        return "publish post"
    
    def _describe_like_post(self) -> str:
        """Like post - includes post info."""
        post_content = self.action_args.get("post_content", "")
        post_author = self.action_args.get("post_author_name", "")
        
        if post_content and post_author:
            return f"like {post_author} post: '{post_content}'"
        elif post_content:
            return f"like post: '{post_content}'"
        elif post_author:
            return f"like {post_author} post"
        return "like post"
    
    def _describe_dislike_post(self) -> str:
        """Dislike post - includes post info."""
        post_content = self.action_args.get("post_content", "")
        post_author = self.action_args.get("post_author_name", "")
        
        if post_content and post_author:
            return f"dislike {post_author} post: '{post_content}'"
        elif post_content:
            return f"dislike post: '{post_content}'"
        elif post_author:
            return f"dislike {post_author} post"
        return "dislike post"
    
    def _describe_repost(self) -> str:
        """Repost - includes content info."""
        original_content = self.action_args.get("original_content", "")
        original_author = self.action_args.get("original_author_name", "")
        
        if original_content and original_author:
            return f"repost {original_author} post: '{original_content}'"
        elif original_content:
            return f"repost post: '{original_content}'"
        elif original_author:
            return f"repost {original_author} post"
        return "repost post"
    
    def _describe_quote_post(self) -> str:
        """Quote post - includes content and quote comment."""
        original_content = self.action_args.get("original_content", "")
        original_author = self.action_args.get("original_author_name", "")
        quote_content = self.action_args.get("quote_content", "") or self.action_args.get("content", "")
        
        base = ""
        if original_content and original_author:
            base = f"quote {original_author} post: '{original_content}'"
        elif original_content:
            base = f"quote post: '{original_content}'"
        elif original_author:
            base = f"quote {original_author} post"
        else:
            base = "quote post"
        
        if quote_content:
            base += f", comment: '{quote_content}'"
        return base
    
    def _describe_follow(self) -> str:
        """Follow user - includes target username."""
        target_user_name = self.action_args.get("target_user_name", "")
        
        if target_user_name:
            return f"follow user '{target_user_name}'"
        return "follow user"
    
    def _describe_create_comment(self) -> str:
        """Create comment - includes comment content and post info."""
        content = self.action_args.get("content", "")
        post_content = self.action_args.get("post_content", "")
        post_author = self.action_args.get("post_author_name", "")
        
        if content:
            if post_content and post_author:
                return f"comment on {post_author} post '{post_content}': '{content}'"
            elif post_content:
                return f"comment on post '{post_content}': '{content}'"
            elif post_author:
                return f"comment on {post_author} post: '{content}'"
            return f"comment: '{content}'"
        return "create comment"
    
    def _describe_like_comment(self) -> str:
        """Like comment - includes comment content info."""
        comment_content = self.action_args.get("comment_content", "")
        comment_author = self.action_args.get("comment_author_name", "")
        
        if comment_content and comment_author:
            return f"like {comment_author} comment: '{comment_content}'"
        elif comment_content:
            return f"like comment: '{comment_content}'"
        elif comment_author:
            return f"like {comment_author} comment"
        return "like comment"
    
    def _describe_dislike_comment(self) -> str:
        """Dislike comment - includes comment content info."""
        comment_content = self.action_args.get("comment_content", "")
        comment_author = self.action_args.get("comment_author_name", "")
        
        if comment_content and comment_author:
            return f"dislike {comment_author} comment: '{comment_content}'"
        elif comment_content:
            return f"dislike comment: '{comment_content}'"
        elif comment_author:
            return f"dislike {comment_author} comment"
        return "dislike comment"
    
    def _describe_search(self) -> str:
        """Search posts - includes search query."""
        query = self.action_args.get("query", "") or self.action_args.get("keyword", "")
        return f"search '{query}'" if query else "search posts"
    
    def _describe_search_user(self) -> str:
        """Search user - includes search query."""
        query = self.action_args.get("query", "") or self.action_args.get("username", "")
        return f"search user '{query}'" if query else "search user"
    
    def _describe_mute(self) -> str:
        """Mute user - includes target username."""
        target_user_name = self.action_args.get("target_user_name", "")
        
        if target_user_name:
            return f"mute user '{target_user_name}'"
        return "mute user"
    
    def _describe_generic(self) -> str:
        # Unknown action type, generate generic description
        return f"performed {self.action_type} action"


class ZepGraphMemoryUpdater:
    """
    Zep graph memory updater.

    Reads simulation action log files, converts new agent activities, and updates
    the Zep graph. Activities are grouped by platform and sent in batches of
    BATCH_SIZE to Zep.

    All behavior types are sent to Zep. action_args include complete context:
    - like/dislike post content
    - repost/quote post content
    - follow/mute user info
    - like/dislike comment content
    """

    # Batch size (per platform)
    BATCH_SIZE = 5

    # Platform display names (for logging)
    PLATFORM_DISPLAY_NAMES = {
        'twitter': 'Platform 1',
        'reddit': 'Platform 2',
    }

    # Send interval (seconds), to avoid rate limiting
    SEND_INTERVAL = 0.5

    # Retry config
    MAX_RETRIES = 3
    RETRY_DELAY = 2 # seconds
    
    def __init__(self, graph_id: str, api_key: Optional[str] = None):
        """
        Initialize the graph memory updater.

        Args:
            graph_id: Zep graph ID
            api_key: Zep API Key (optional, defaults to config value)
        """
        self.graph_id = graph_id
        self.api_key = api_key or Config.ZEP_API_KEY
        
        if not self.api_key:
            raise ValueError("ZEP_API_KEY not yet configured")
        
        from zep_cloud.client import Zep
        self.client = Zep(api_key=self.api_key)
        
        # Activity queue
        self._activity_queue: Queue = Queue()

        # Platform buffers (each platform accumulates up to BATCH_SIZE)
        self._platform_buffers: Dict[str, List[AgentActivity]] = {
            'twitter': [],
            'reddit': [],
        }
        self._buffer_lock = threading.Lock()

        # Worker state
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None

        # Statistics
        self._total_activities = 0    # Total activities added to queue
        self._total_sent = 0          # Successfully sent batches to Zep
        self._total_items_sent = 0    # Successfully sent individual items to Zep
        self._failed_count = 0        # Failed batch count
        self._skipped_count = 0       # Skipped activities (e.g., DO_NOTHING)
        
        logger.info(f"ZepGraphMemoryUpdater initialized: graph_id={graph_id}, batch_size={self.BATCH_SIZE}")

    def _get_platform_display_name(self, platform: str) -> str:
        """Get the display name for a platform."""
        return self.PLATFORM_DISPLAY_NAMES.get(platform.lower(), platform)
    
    def start(self):
        """Start the background worker thread."""
        if self._running:
            return
        
        self._running = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name=f"ZepMemoryUpdater-{self.graph_id[:8]}"
        )
        self._worker_thread.start()
        logger.info(f"ZepGraphMemoryUpdater started: graph_id={self.graph_id}")
    
    def stop(self):
        """Stop the background worker thread."""
        self._running = False

        # Flush remaining activities
        self._flush_remaining()
        
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=10)
        
        logger.info(f"ZepGraphMemoryUpdater stopped: graph_id={self.graph_id}, "
                   f"total_activities={self._total_activities}, "
                   f"batches_sent={self._total_sent}, "
                   f"items_sent={self._total_items_sent}, "
                   f"failed={self._failed_count}, "
                   f"skipped={self._skipped_count}")
    
    def add_activity(self, activity: AgentActivity):
        """
        Add an agent activity to the processing queue.

        All behavior types are added, including:
        - CREATE_POST (create post)
        - CREATE_COMMENT (create comment)
        - QUOTE_POST (quote post)
        - SEARCH_POSTS (search posts)
        - SEARCH_USER (search users)
        - LIKE_POST/DISLIKE_POST (like/dislike post)
        - REPOST (repost)
        - FOLLOW (follow user)
        - MUTE (mute user)
        - LIKE_COMMENT/DISLIKE_COMMENT (like/dislike comment)

        action_args include complete context info (post content, user names, etc.).

        Args:
            activity: Agent activity record
        """
        # Skip DO_NOTHING action type
        if activity.action_type == "DO_NOTHING":
            self._skipped_count += 1
            return
        
        self._activity_queue.put(activity)
        self._total_activities += 1
        logger.debug(f"Added to Zep queue: {activity.agent_name} - {activity.action_type}")
    
    def add_activity_from_dict(self, data: Dict[str, Any], platform: str):
        """
        Create and add an activity from raw dictionary data.

        Args:
            data: Parsed data from actions.jsonl
            platform: Platform name (twitter/reddit)
        """
        # Skip event-type entries
        if "event_type" in data:
            return
        
        activity = AgentActivity(
            platform=platform,
            agent_id=data.get("agent_id", 0),
            agent_name=data.get("agent_name", ""),
            action_type=data.get("action_type", ""),
            action_args=data.get("action_args", {}),
            round_num=data.get("round", 0),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
        )
        
        self.add_activity(activity)
    
    def _worker_loop(self):
        """Background worker loop - groups activities by platform and sends to Zep."""
        while self._running or not self._activity_queue.empty():
            try:
                # Get from queue (timeout 1 second)
                try:
                    activity = self._activity_queue.get(timeout=1)
                    
                    # Add to platform buffer
                    platform = activity.platform.lower()
                    with self._buffer_lock:
                        if platform not in self._platform_buffers:
                            self._platform_buffers[platform] = []
                        self._platform_buffers[platform].append(activity)
                        
                        # Check if platform buffer is full
                        if len(self._platform_buffers[platform]) >= self.BATCH_SIZE:
                            batch = self._platform_buffers[platform][:self.BATCH_SIZE]
                            self._platform_buffers[platform] = self._platform_buffers[platform][self.BATCH_SIZE:]
                            # Send the batch
                            self._send_batch_activities(batch, platform)
                            # Wait between sends to avoid rate limiting
                            time.sleep(self.SEND_INTERVAL)
                    
                except Empty:
                    pass
                    
            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                time.sleep(1)
    
    def _send_batch_activities(self, activities: List[AgentActivity], platform: str):
        """
        Send a batch of activities to Zep graph (merged as combined text).

        Args:
            activities: List of agent activities
            platform: Platform name
        """
        if not activities:
            return
        
        # Merge activity texts, separated by newlines
        episode_texts = [activity.to_episode_text() for activity in activities]
        combined_text = "\n".join(episode_texts)
        
        # Retry loop
        for attempt in range(self.MAX_RETRIES):
            try:
                self.client.graph.add(
                    graph_id=self.graph_id,
                    type="text",
                    data=combined_text
                )
                
                self._total_sent += 1
                self._total_items_sent += len(activities)
                display_name = self._get_platform_display_name(platform)
                logger.info(f"Successfully sent {len(activities)} {display_name} activities to graph {self.graph_id}")
                logger.debug(f"Batch content: {combined_text[:200]}...")
                return
                
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    logger.warning(f"Sending to Zep failed (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")
                    time.sleep(self.RETRY_DELAY * (attempt + 1))
                else:
                    logger.error(f"Sending to Zep failed after {self.MAX_RETRIES} retries: {e}")
                    self._failed_count += 1
    
    def _flush_remaining(self):
        """Flush all remaining activities in the queue and buffers."""
        # Drain the queue into platform buffers
        while not self._activity_queue.empty():
            try:
                activity = self._activity_queue.get_nowait()
                platform = activity.platform.lower()
                with self._buffer_lock:
                    if platform not in self._platform_buffers:
                        self._platform_buffers[platform] = []
                    self._platform_buffers[platform].append(activity)
            except Empty:
                break
        
        # Send remaining items per platform (regardless of BATCH_SIZE)
        with self._buffer_lock:
            for platform, buffer in self._platform_buffers.items():
                if buffer:
                    display_name = self._get_platform_display_name(platform)
                    logger.info(f"Flushing {len(buffer)} remaining activities for {display_name} platform")
                    self._send_batch_activities(buffer, platform)
            # Clear all buffers
            for platform in self._platform_buffers:
                self._platform_buffers[platform] = []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get updater statistics."""
        with self._buffer_lock:
            buffer_sizes = {p: len(b) for p, b in self._platform_buffers.items()}
        
        return {
            "graph_id": self.graph_id,
            "batch_size": self.BATCH_SIZE,
            "total_activities": self._total_activities,      # Total added to queue
            "batches_sent": self._total_sent,                # Successfully sent batches
            "items_sent": self._total_items_sent,            # Successfully sent items
            "failed_count": self._failed_count,              # Failed batch count
            "skipped_count": self._skipped_count,            # Skipped (e.g., DO_NOTHING)
            "queue_size": self._activity_queue.qsize(),
            "buffer_sizes": buffer_sizes,                    # Per-platform buffer sizes
            "running": self._running,
        }


class ZepGraphMemoryManager:
    """
    Manager for Zep graph memory updaters across simulations.

    Each simulation gets its own updater instance.
    """
    
    _updaters: Dict[str, ZepGraphMemoryUpdater] = {}
    _lock = threading.Lock()
    
    @classmethod
    def create_updater(cls, simulation_id: str, graph_id: str) -> ZepGraphMemoryUpdater:
        """
        Create a graph memory updater for a simulation.

        Args:
            simulation_id: Simulation ID
            graph_id: Zep graph ID

        Returns:
            ZepGraphMemoryUpdater instance
        """
        with cls._lock:
            # If already exists, stop the old updater first
            if simulation_id in cls._updaters:
                cls._updaters[simulation_id].stop()
            
            updater = ZepGraphMemoryUpdater(graph_id)
            updater.start()
            cls._updaters[simulation_id] = updater
            cls._stop_all_done = False  # Reset so future stop_all() calls work
            
            logger.info(f"Created graph updater: simulation_id={simulation_id}, graph_id={graph_id}")
            return updater
    
    @classmethod
    def get_updater(cls, simulation_id: str) -> Optional[ZepGraphMemoryUpdater]:
        """Get the updater for a simulation."""
        return cls._updaters.get(simulation_id)
    
    @classmethod
    def stop_updater(cls, simulation_id: str):
        """Stop and remove the updater for a simulation."""
        with cls._lock:
            if simulation_id in cls._updaters:
                cls._updaters[simulation_id].stop()
                del cls._updaters[simulation_id]
                logger.info(f"Stopped graph updater: simulation_id={simulation_id}")
    
    # Prevent duplicate stop_all calls
    _stop_all_done = False
    
    @classmethod
    def stop_all(cls):
        """Stop all updaters."""
        # Prevent duplicate calls
        if cls._stop_all_done:
            return
        cls._stop_all_done = True
        
        with cls._lock:
            if cls._updaters:
                for simulation_id, updater in list(cls._updaters.items()):
                    try:
                        updater.stop()
                    except Exception as e:
                        logger.error(f"Failed to stop updater: simulation_id={simulation_id}, error={e}")
                cls._updaters.clear()
            logger.info("All graph memory updaters stopped")
    
    @classmethod
    def get_all_stats(cls) -> Dict[str, Dict[str, Any]]:
        """Get all updater statistics."""
        return {
            sim_id: updater.get_stats() 
            for sim_id, updater in cls._updaters.items()
        }
