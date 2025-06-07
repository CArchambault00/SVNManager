"""
Utility functions for working with Text widgets
"""
import tkinter as tk

def ensure_text_widget_visible(text_widget: tk.Text, content: str = None) -> None:
    """
    Ensures a Text widget is properly rendered and its content is visible.
    
    Args:
        text_widget: The Text widget to manage
        content: Optional content to set in the widget
    """
    # First ensure the widget is mapped
    text_widget.update_idletasks()
    
    # Clear any existing content
    text_widget.delete("1.0", tk.END)
    
    if content is not None:
        # Insert the new content
        text_widget.insert("1.0", content)
        
        # Force the widget to update and render
        text_widget.update()
        
        # Make sure the widget is visible and has focus
        text_widget.see("1.0")
        
        # Force the parent to update layout
        parent = text_widget.master
        while parent:
            try:
                parent.update_idletasks()
                parent = parent.master
            except:
                break
    
    # Final update to ensure visibility
    text_widget.update()

def get_text_content(text_widget: tk.Text) -> str:
    """
    Get content from a Text widget, properly handling line endings.
    
    Args:
        text_widget: The Text widget to get content from
        
    Returns:
        The text content with proper line endings
    """
    content = text_widget.get("1.0", tk.END)
    # Remove trailing newline if it exists (tkinter adds one)
    if content.endswith('\n'):
        content = content[:-1]
    return content
