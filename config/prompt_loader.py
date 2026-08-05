"""
Prompt loading and management system.

Handles loading prompts from YAML, template rendering, and caching.
"""

import re
from pathlib import Path
from typing import Dict, Any, Optional
from functools import lru_cache

import yaml


class PromptLoader:
    """
    Manages loading and rendering of prompts from YAML files.
    
    Features:
    - Load prompts from YAML
    - Template rendering with variable substitution
    - Caching for performance
    - Validation
    
    Example:
        loader = PromptLoader()
        prompt = loader.get_prompt("system_prompts.intake_agent")
        template = loader.render_template(
            "templates.classify_ticket",
            message="I need help with my password"
        )
    """
    
    def __init__(self, prompts_path: Optional[Path] = None):
        """
        Initialize prompt loader.
        
        Args:
            prompts_path: Path to prompts.yaml file. If None, uses default location.
        """
        if prompts_path is None:
            prompts_path = Path(__file__).parent / "prompts.yaml"
        
        self.prompts_path = prompts_path
        self._prompts: Optional[Dict[str, Any]] = None
    
    def _load_prompts(self) -> Dict[str, Any]:
        """
        Load prompts from YAML file.
        
        Returns:
            Dictionary of prompts
            
        Raises:
            FileNotFoundError: If prompts file doesn't exist
            yaml.YAMLError: If YAML is malformed
        """
        if not self.prompts_path.exists():
            raise FileNotFoundError(
                f"Prompts file not found: {self.prompts_path}"
            )
        
        with open(self.prompts_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    @property
    def prompts(self) -> Dict[str, Any]:
        """Lazy-load and cache prompts."""
        if self._prompts is None:
            self._prompts = self._load_prompts()
        return self._prompts
    
    def reload(self) -> None:
        """Reload prompts from file (useful in development)."""
        self._prompts = None
        # Clear LRU cache
        self.get_cached_prompt.cache_clear()
    
    def get_prompt(self, path: str) -> str:
        """
        Get a prompt by dot-notation path.
        
        Args:
            path: Dot-separated path (e.g., "system_prompts.intake_agent")
            
        Returns:
            Prompt string
            
        Raises:
            KeyError: If prompt path doesn't exist
            
        Example:
            >>> loader.get_prompt("system_prompts.intake_agent")
            'You are an Intake Agent...'
        """
        parts = path.split('.')
        value = self.prompts
        
        for part in parts:
            if not isinstance(value, dict):
                raise KeyError(
                    f"Invalid path '{path}': '{'.'.join(parts[:parts.index(part)])}' "
                    f"is not a dictionary"
                )
            if part not in value:
                raise KeyError(f"Prompt not found: {path}")
            value = value[part]
        
        if not isinstance(value, str):
            raise KeyError(f"Path '{path}' does not point to a string prompt")
        
        return value.strip()
    
    @lru_cache(maxsize=128)
    def get_cached_prompt(self, path: str) -> str:
        """
        Get a prompt with caching (for frequently accessed prompts).
        
        Args:
            path: Dot-separated path
            
        Returns:
            Prompt string
        """
        return self.get_prompt(path)
    
    def render_template(
        self,
        template_path: str,
        **kwargs: Any
    ) -> str:
        """
        Render a template with variable substitution.
        
        Args:
            template_path: Path to template (e.g., "templates.classify_ticket")
            **kwargs: Variables to substitute in template
            
        Returns:
            Rendered template string
            
        Example:
            >>> loader.render_template(
            ...     "templates.classify_ticket",
            ...     message="I forgot my password",
            ...     context=""
            ... )
            'Classify this customer message...'
        """
        template = self.get_prompt(template_path)
        
        # Find all variables in template
        variables = re.findall(r'\{(\w+)\}', template)
        
        # Check for missing variables
        missing = set(variables) - set(kwargs.keys())
        if missing:
            raise ValueError(
                f"Missing template variables: {missing}. "
                f"Template requires: {variables}"
            )
        
        # Substitute variables
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Template rendering failed: {e}")
    
    def get_system_prompt(self, agent_name: str) -> str:
        """
        Get system prompt for an agent.
        
        Args:
            agent_name: Agent name (e.g., "intake_agent", "resolution_agent")
            
        Returns:
            System prompt string
            
        Example:
            >>> loader.get_system_prompt("intake_agent")
            'You are an Intake Agent...'
        """
        return self.get_prompt(f"system_prompts.{agent_name}")
    
    def get_error_message(self, error_type: str, **kwargs: Any) -> str:
        """
        Get an error message with optional variable substitution.
        
        Args:
            error_type: Error type (e.g., "generic_error", "llm_timeout")
            **kwargs: Variables for substitution
            
        Returns:
            Error message string
        """
        message = self.get_prompt(f"error_messages.{error_type}")
        
        if kwargs:
            return message.format(**kwargs)
        return message
    
    def get_greeting(self, greeting_type: str, **kwargs: Any) -> str:
        """
        Get a greeting message.
        
        Args:
            greeting_type: Greeting type (e.g., "first_time", "returning")
            **kwargs: Variables for substitution
            
        Returns:
            Greeting message string
        """
        greeting = self.get_prompt(f"greetings.{greeting_type}")
        return greeting.format(**kwargs)
    
    def get_closing(self, closing_type: str, **kwargs: Any) -> str:
        """
        Get a closing message.
        
        Args:
            closing_type: Closing type (e.g., "resolved", "escalated")
            **kwargs: Variables for substitution
            
        Returns:
            Closing message string
        """
        closing = self.get_prompt(f"closings.{closing_type}")
        return closing.format(**kwargs)
    
    def list_prompts(self, prefix: Optional[str] = None) -> list[str]:
        """
        List all available prompt paths.
        
        Args:
            prefix: Optional prefix to filter by (e.g., "system_prompts")
            
        Returns:
            List of prompt paths
        """
        def _flatten(d: Dict, parent_key: str = '') -> list[str]:
            """Recursively flatten nested dict to dot-notation paths."""
            items = []
            for k, v in d.items():
                new_key = f"{parent_key}.{k}" if parent_key else k
                if isinstance(v, dict):
                    items.extend(_flatten(v, new_key))
                elif isinstance(v, str):
                    items.append(new_key)
            return items
        
        all_prompts = _flatten(self.prompts)
        
        if prefix:
            return [p for p in all_prompts if p.startswith(prefix)]
        return all_prompts
    
    def validate_prompts(self) -> Dict[str, list[str]]:
        """
        Validate all prompts for common issues.
        
        Returns:
            Dictionary of issues found (empty if all valid)
            
        Example:
            >>> issues = loader.validate_prompts()
            >>> if issues:
            ...     print("Validation issues:", issues)
        """
        issues: Dict[str, list[str]] = {}
        
        for path in self.list_prompts():
            try:
                prompt = self.get_prompt(path)
                
                # Check for empty prompts
                if not prompt.strip():
                    issues.setdefault('empty_prompts', []).append(path)
                
                # Check for unclosed template variables
                open_braces = prompt.count('{')
                close_braces = prompt.count('}')
                if open_braces != close_braces:
                    issues.setdefault('unmatched_braces', []).append(path)
                
                # Check for very short prompts (might be incomplete)
                if len(prompt) < 50 and 'error_messages' not in path:
                    issues.setdefault('suspiciously_short', []).append(path)
                
            except Exception as e:
                issues.setdefault('load_errors', []).append(f"{path}: {e}")
        
        return issues


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

# Global prompt loader instance
_prompt_loader: Optional[PromptLoader] = None


def get_prompt_loader() -> PromptLoader:
    """
    Get global prompt loader instance (singleton pattern).
    
    Returns:
        PromptLoader instance
    """
    global _prompt_loader
    if _prompt_loader is None:
        _prompt_loader = PromptLoader()
    return _prompt_loader


# Convenience functions for common operations

def get_prompt(path: str) -> str:
    """Get a prompt by path."""
    return get_prompt_loader().get_prompt(path)


def render_template(template_path: str, **kwargs: Any) -> str:
    """Render a template with variables."""
    return get_prompt_loader().render_template(template_path, **kwargs)


def get_system_prompt(agent_name: str) -> str:
    """Get system prompt for an agent."""
    return get_prompt_loader().get_system_prompt(agent_name)


def reload_prompts() -> None:
    """Reload prompts from file (useful in development)."""
    get_prompt_loader().reload()