from .email_composer_deep_research import DeepResearchEmailComposer

# Lazy initialization to avoid import-time failures
_composer = None

def get_composer():
    """Get or create the shared composer instance."""
    global _composer
    if _composer is None:
        _composer = DeepResearchEmailComposer()
    return _composer

# For backward compatibility, create a property that behaves like the old instance
class _ComposerProxy:
    def __getattr__(self, name):
        return getattr(get_composer(), name)

composer = _ComposerProxy() 