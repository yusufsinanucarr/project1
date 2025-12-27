"""
NoteEditor module with advanced features for note editing and management.

Features:
- Auto-save functionality with configurable intervals
- Undo-Redo system with full history tracking
- Search functionality with regex support
- Tagging system for note organization
- Theme support (light/dark modes)
- Thread-safe operations
"""

import threading
import time
import re
from collections import deque
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import json


class Theme(Enum):
    """Available themes for the note editor."""
    LIGHT = "light"
    DARK = "dark"


@dataclass
class EditorState:
    """Represents a state snapshot for undo/redo operations."""
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    cursor_position: int = 0
    
    def __eq__(self, other):
        if not isinstance(other, EditorState):
            return False
        return (self.content == other.content and 
                self.tags == other.tags and 
                self.cursor_position == other.cursor_position)


class UndoRedoManager:
    """Manages undo and redo operations with a history stack."""
    
    def __init__(self, max_history: int = 100):
        """
        Initialize the undo/redo manager.
        
        Args:
            max_history: Maximum number of states to keep in history
        """
        self.max_history = max_history
        self.undo_stack: deque = deque(maxlen=max_history)
        self.redo_stack: deque = deque(maxlen=max_history)
    
    def push(self, state: EditorState) -> None:
        """Push a new state to the undo stack and clear redo stack."""
        self.undo_stack.append(state)
        self.redo_stack.clear()
    
    def undo(self) -> Optional[EditorState]:
        """Pop and return the last undo state."""
        if not self.undo_stack:
            return None
        state = self.undo_stack.pop()
        self.redo_stack.append(state)
        return state
    
    def redo(self) -> Optional[EditorState]:
        """Pop and return the last redo state."""
        if not self.redo_stack:
            return None
        state = self.redo_stack.pop()
        self.undo_stack.append(state)
        return state
    
    def can_undo(self) -> bool:
        """Check if undo is available."""
        return len(self.undo_stack) > 0
    
    def can_redo(self) -> bool:
        """Check if redo is available."""
        return len(self.redo_stack) > 0
    
    def clear(self) -> None:
        """Clear all history."""
        self.undo_stack.clear()
        self.redo_stack.clear()


class SearchEngine:
    """Handles search and replace operations with regex support."""
    
    def __init__(self):
        self.search_pattern: Optional[re.Pattern] = None
        self.last_search: str = ""
        self.case_sensitive: bool = False
    
    def find_all(self, text: str, pattern: str, 
                 case_sensitive: bool = False) -> List[Tuple[int, int]]:
        """
        Find all occurrences of a pattern in text.
        
        Args:
            text: The text to search in
            pattern: The search pattern (supports regex)
            case_sensitive: Whether search is case-sensitive
        
        Returns:
            List of (start, end) tuples for each match
        """
        self.last_search = pattern
        self.case_sensitive = case_sensitive
        
        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            regex = re.compile(pattern, flags)
            matches = [(m.start(), m.end()) for m in regex.finditer(text)]
            return matches
        except re.error:
            return []
    
    def find_next(self, text: str, pattern: str, 
                  from_position: int = 0) -> Optional[Tuple[int, int]]:
        """
        Find the next occurrence of a pattern from a given position.
        
        Args:
            text: The text to search in
            pattern: The search pattern
            from_position: Starting position for search
        
        Returns:
            (start, end) tuple or None if not found
        """
        matches = self.find_all(text, pattern, self.case_sensitive)
        for match_start, match_end in matches:
            if match_start >= from_position:
                return (match_start, match_end)
        return None
    
    def replace(self, text: str, pattern: str, replacement: str,
                replace_all: bool = False) -> str:
        """
        Replace pattern occurrences with replacement text.
        
        Args:
            text: The text to process
            pattern: The pattern to find
            replacement: The replacement text
            replace_all: Whether to replace all occurrences
        
        Returns:
            Modified text
        """
        try:
            flags = 0 if self.case_sensitive else re.IGNORECASE
            regex = re.compile(pattern, flags)
            
            if replace_all:
                return regex.sub(replacement, text)
            else:
                return regex.sub(replacement, text, count=1)
        except re.error:
            return text


class TagManager:
    """Manages tags for organizing notes."""
    
    def __init__(self):
        self.tags: Dict[str, List[str]] = {}  # tag -> list of tag details
        self.tag_index: Dict[str, int] = {}  # tag -> frequency
    
    def add_tag(self, tag: str) -> bool:
        """
        Add a new tag.
        
        Args:
            tag: Tag name to add
        
        Returns:
            True if tag was added, False if already exists
        """
        if tag and tag not in self.tag_index:
            self.tag_index[tag] = 0
            self.tags[tag] = []
            return True
        return False
    
    def remove_tag(self, tag: str) -> bool:
        """
        Remove a tag.
        
        Args:
            tag: Tag name to remove
        
        Returns:
            True if tag was removed, False if not found
        """
        if tag in self.tag_index:
            del self.tag_index[tag]
            del self.tags[tag]
            return True
        return False
    
    def get_all_tags(self) -> List[str]:
        """Get all available tags."""
        return list(self.tag_index.keys())
    
    def increment_tag_usage(self, tag: str) -> None:
        """Increment the usage count for a tag."""
        if tag in self.tag_index:
            self.tag_index[tag] += 1
    
    def get_tags_by_frequency(self, limit: Optional[int] = None) -> List[Tuple[str, int]]:
        """Get tags sorted by usage frequency."""
        sorted_tags = sorted(self.tag_index.items(), 
                           key=lambda x: x[1], 
                           reverse=True)
        return sorted_tags[:limit] if limit else sorted_tags


class NoteEditor:
    """
    Advanced note editor with multiple features including auto-save,
    undo-redo, search, tagging, and theme support.
    """
    
    def __init__(self, auto_save_interval: int = 30):
        """
        Initialize the NoteEditor.
        
        Args:
            auto_save_interval: Interval in seconds for auto-save (0 to disable)
        """
        # Core content
        self.content: str = ""
        self.title: str = ""
        self.created_at: datetime = datetime.now()
        self.modified_at: datetime = datetime.now()
        
        # Feature managers
        self.undo_redo = UndoRedoManager()
        self.search_engine = SearchEngine()
        self.tag_manager = TagManager()
        
        # State management
        self.current_state: EditorState = EditorState(content="")
        self.cursor_position: int = 0
        self.selection_start: int = 0
        self.selection_end: int = 0
        
        # Theme
        self.theme: Theme = Theme.LIGHT
        
        # Auto-save configuration
        self.auto_save_interval: int = auto_save_interval
        self.auto_save_enabled: bool = auto_save_interval > 0
        self.last_save_time: datetime = datetime.now()
        self.on_auto_save: Optional[Callable[[str], None]] = None
        
        # Threading
        self._lock = threading.RLock()
        self._auto_save_thread: Optional[threading.Thread] = None
        self._stop_auto_save: bool = False
        
        # Change tracking
        self.is_modified: bool = False
        self.modification_callbacks: List[Callable[[], None]] = []
        
        if self.auto_save_enabled:
            self._start_auto_save()
    
    def _start_auto_save(self) -> None:
        """Start the auto-save background thread."""
        if self._auto_save_thread is None or not self._auto_save_thread.is_alive():
            self._stop_auto_save = False
            self._auto_save_thread = threading.Thread(
                target=self._auto_save_worker,
                daemon=True
            )
            self._auto_save_thread.start()
    
    def _auto_save_worker(self) -> None:
        """Worker thread for periodic auto-save."""
        while not self._stop_auto_save:
            time.sleep(self.auto_save_interval)
            if self.is_modified and not self._stop_auto_save:
                self.save()
    
    def _trigger_modification_callbacks(self) -> None:
        """Trigger all registered modification callbacks."""
        for callback in self.modification_callbacks:
            try:
                callback()
            except Exception:
                pass
    
    def set_content(self, content: str, save_state: bool = True) -> None:
        """
        Set the content of the note.
        
        Args:
            content: The new content
            save_state: Whether to save the current state to undo history
        """
        with self._lock:
            if save_state and self.content != content:
                self.undo_redo.push(self.current_state)
            
            self.content = content
            self.modified_at = datetime.now()
            self.is_modified = True
            self.current_state = EditorState(
                content=content,
                cursor_position=self.cursor_position,
                tags=list(self.tag_manager.get_all_tags())
            )
            self._trigger_modification_callbacks()
    
    def insert_text(self, text: str, position: Optional[int] = None) -> None:
        """
        Insert text at a specific position.
        
        Args:
            text: Text to insert
            position: Position to insert at (default: current cursor position)
        """
        with self._lock:
            pos = position if position is not None else self.cursor_position
            self.undo_redo.push(self.current_state)
            
            self.content = (self.content[:pos] + text + 
                          self.content[pos:])
            self.cursor_position = pos + len(text)
            self.modified_at = datetime.now()
            self.is_modified = True
            self.current_state = EditorState(
                content=self.content,
                cursor_position=self.cursor_position,
                tags=list(self.tag_manager.get_all_tags())
            )
            self._trigger_modification_callbacks()
    
    def delete_range(self, start: int, end: int) -> None:
        """
        Delete text in a range.
        
        Args:
            start: Start position
            end: End position
        """
        with self._lock:
            self.undo_redo.push(self.current_state)
            
            self.content = self.content[:start] + self.content[end:]
            self.cursor_position = start
            self.modified_at = datetime.now()
            self.is_modified = True
            self.current_state = EditorState(
                content=self.content,
                cursor_position=self.cursor_position,
                tags=list(self.tag_manager.get_all_tags())
            )
            self._trigger_modification_callbacks()
    
    def undo(self) -> bool:
        """
        Undo the last change.
        
        Returns:
            True if undo was successful, False otherwise
        """
        with self._lock:
            state = self.undo_redo.undo()
            if state:
                self.content = state.content
                self.cursor_position = state.cursor_position
                self.is_modified = True
                self.current_state = state
                self._trigger_modification_callbacks()
                return True
            return False
    
    def redo(self) -> bool:
        """
        Redo the last undone change.
        
        Returns:
            True if redo was successful, False otherwise
        """
        with self._lock:
            state = self.undo_redo.redo()
            if state:
                self.content = state.content
                self.cursor_position = state.cursor_position
                self.is_modified = True
                self.current_state = state
                self._trigger_modification_callbacks()
                return True
            return False
    
    def can_undo(self) -> bool:
        """Check if undo is available."""
        with self._lock:
            return self.undo_redo.can_undo()
    
    def can_redo(self) -> bool:
        """Check if redo is available."""
        with self._lock:
            return self.undo_redo.can_redo()
    
    def search(self, pattern: str, case_sensitive: bool = False) -> List[Tuple[int, int]]:
        """
        Search for all occurrences of a pattern.
        
        Args:
            pattern: Search pattern (supports regex)
            case_sensitive: Whether search is case-sensitive
        
        Returns:
            List of (start, end) tuples for matches
        """
        with self._lock:
            return self.search_engine.find_all(self.content, pattern, case_sensitive)
    
    def search_next(self, pattern: str, 
                   from_position: Optional[int] = None) -> Optional[Tuple[int, int]]:
        """
        Find the next occurrence of a pattern.
        
        Args:
            pattern: Search pattern
            from_position: Position to search from (default: current cursor position)
        
        Returns:
            (start, end) tuple or None if not found
        """
        with self._lock:
            pos = from_position if from_position is not None else self.cursor_position
            return self.search_engine.find_next(self.content, pattern, pos)
    
    def replace(self, pattern: str, replacement: str, 
                replace_all: bool = False) -> Tuple[int, str]:
        """
        Replace pattern occurrences.
        
        Args:
            pattern: Pattern to find
            replacement: Replacement text
            replace_all: Whether to replace all occurrences
        
        Returns:
            Tuple of (number of replacements, new content)
        """
        with self._lock:
            self.undo_redo.push(self.current_state)
            
            old_content = self.content
            new_content = self.search_engine.replace(
                self.content, 
                pattern, 
                replacement, 
                replace_all
            )
            
            # Count replacements
            count = len(self.search_engine.find_all(old_content, pattern)) - \
                   len(self.search_engine.find_all(new_content, pattern))
            
            if count > 0:
                self.content = new_content
                self.modified_at = datetime.now()
                self.is_modified = True
                self.current_state = EditorState(
                    content=self.content,
                    cursor_position=self.cursor_position,
                    tags=list(self.tag_manager.get_all_tags())
                )
                self._trigger_modification_callbacks()
            
            return (count, self.content)
    
    def add_tag(self, tag: str) -> bool:
        """
        Add a tag to the note.
        
        Args:
            tag: Tag name to add
        
        Returns:
            True if tag was added, False if already exists
        """
        with self._lock:
            result = self.tag_manager.add_tag(tag)
            if result:
                self.modified_at = datetime.now()
            return result
    
    def remove_tag(self, tag: str) -> bool:
        """
        Remove a tag from the note.
        
        Args:
            tag: Tag name to remove
        
        Returns:
            True if tag was removed, False if not found
        """
        with self._lock:
            result = self.tag_manager.remove_tag(tag)
            if result:
                self.modified_at = datetime.now()
            return result
    
    def get_tags(self) -> List[str]:
        """Get all tags for the note."""
        with self._lock:
            return self.tag_manager.get_all_tags()
    
    def get_popular_tags(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get the most frequently used tags."""
        with self._lock:
            return self.tag_manager.get_tags_by_frequency(limit)
    
    def set_theme(self, theme: Theme) -> None:
        """
        Set the editor theme.
        
        Args:
            theme: The theme to apply
        """
        with self._lock:
            self.theme = theme
    
    def get_theme(self) -> Theme:
        """Get the current theme."""
        with self._lock:
            return self.theme
    
    def set_cursor_position(self, position: int) -> None:
        """
        Set the cursor position.
        
        Args:
            position: New cursor position
        """
        with self._lock:
            self.cursor_position = max(0, min(position, len(self.content)))
    
    def get_cursor_position(self) -> int:
        """Get the current cursor position."""
        with self._lock:
            return self.cursor_position
    
    def save(self) -> None:
        """Save the note (triggers auto-save callback if configured)."""
        with self._lock:
            if self.on_auto_save and self.is_modified:
                self.on_auto_save(self.content)
            self.last_save_time = datetime.now()
            self.is_modified = False
    
    def get_content(self) -> str:
        """Get the current content."""
        with self._lock:
            return self.content
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the note."""
        with self._lock:
            words = len(self.content.split())
            lines = len(self.content.split('\n'))
            characters = len(self.content)
            
            return {
                'characters': characters,
                'words': words,
                'lines': lines,
                'created_at': self.created_at.isoformat(),
                'modified_at': self.modified_at.isoformat(),
                'last_saved': self.last_save_time.isoformat(),
                'theme': self.theme.value,
                'is_modified': self.is_modified,
                'tags_count': len(self.tag_manager.get_all_tags()),
                'undo_available': self.undo_redo.can_undo(),
                'redo_available': self.undo_redo.can_redo(),
            }
    
    def register_modification_callback(self, callback: Callable[[], None]) -> None:
        """
        Register a callback to be called when content is modified.
        
        Args:
            callback: Function to call on modification
        """
        with self._lock:
            self.modification_callbacks.append(callback)
    
    def clear_history(self) -> None:
        """Clear the undo/redo history."""
        with self._lock:
            self.undo_redo.clear()
    
    def export_as_json(self) -> str:
        """Export the note as JSON."""
        with self._lock:
            data = {
                'title': self.title,
                'content': self.content,
                'tags': self.get_tags(),
                'created_at': self.created_at.isoformat(),
                'modified_at': self.modified_at.isoformat(),
                'theme': self.theme.value,
            }
            return json.dumps(data, indent=2)
    
    def shutdown(self) -> None:
        """Shutdown the editor and stop auto-save thread."""
        self._stop_auto_save = True
        self.save()
        if self._auto_save_thread and self._auto_save_thread.is_alive():
            self._auto_save_thread.join(timeout=5)
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()
        return False
