# Documentation Strategy

This document outlines our documentation approach for the AI Customer Service project.

## 📋 Documentation Philosophy

**Goal:** Every component should be fully documented when completed, making onboarding and maintenance effortless.

**Principles:**
1. **Document as you build** - Don't defer documentation
2. **Two-tier system** - Quick reference + detailed guide
3. **Examples over explanation** - Show, don't just tell
4. **Keep it current** - Update docs with code changes
5. **Test your docs** - Examples should actually work

## 🏗️ Documentation Structure

### Two-Tier System

Every major component has TWO documentation files:

#### 1. Quick Reference (`component/README.md`)
- **Location:** In the component's folder
- **Purpose:** Fast lookup for developers working in that area
- **Length:** 1-2 pages max
- **Contains:**
  - File structure
  - Quick start examples
  - Common operations
  - Link to detailed docs

**Example:** `config/README.md`

#### 2. Detailed Guide (`docs/component.md`)
- **Location:** In the `docs/` folder
- **Purpose:** Comprehensive understanding
- **Length:** As long as needed (typically 5-15 pages)
- **Contains:**
  - Overview and architecture
  - Complete API reference
  - All configuration options
  - Testing instructions
  - Troubleshooting guide
  - Best practices

**Example:** `docs/configuration.md`

### Directory Structure

```
project/
├── README.md                    # Project overview, quick start
├── DOCUMENTATION_STRATEGY.md    # This file
│
├── docs/                        # Detailed documentation
│   ├── README.md               # Documentation index
│   ├── configuration.md        # Config system guide
│   ├── models.md              # Data models guide
│   ├── agents.md              # Agent development guide
│   ├── architecture.md        # System architecture
│   ├── api_reference.md       # API documentation
│   ├── deployment.md          # Deployment guide
│   └── troubleshooting.md     # Common issues
│
├── config/                     # Configuration component
│   └── README.md              # Quick config reference
│
├── src/models/                 # Models component
│   └── README.md              # Quick models reference
│
└── src/agents/                 # Agents component
    ├── README.md              # Quick agents reference
    ├── intake/
    │   └── README.md          # Intake agent specifics
    └── resolution/
        └── README.md          # Resolution agent specifics
```

## ✍️ Writing Documentation

### When to Document

**Immediately after completing a component:**
1. Write quick reference (`component/README.md`)
2. Write detailed guide (`docs/component.md`)
3. Update `docs/README.md` index
4. Update main `README.md` if needed

**During development:**
- Add inline code comments for complex logic
- Write docstrings for all public functions/classes
- Add type hints everywhere

### Documentation Template

#### Quick Reference Template

```markdown
# [Component Name]

Quick reference for [component]. See [detailed docs](../docs/component.md) for more.

## 📁 Files
[List of files with brief descriptions]

## 🚀 Quick Start
[Minimal working example]

## 🔧 Common Operations
[3-5 most common use cases with code]

## 📚 Full Documentation
Link to detailed guide
```

#### Detailed Guide Template

```markdown
# [Component Name]

Complete guide to [component].

## 📋 Table of Contents
[Auto-generated or manual TOC]

## Overview
[What is this component? Why does it exist?]

## Quick Start
[Get running in 5 minutes]

## Architecture
[How it works internally]

## API Reference
[Complete API with all options]

## Usage Examples
[Real-world examples]

## Testing
[How to test this component]

## Troubleshooting
[Common issues and solutions]

## Best Practices
[Dos and don'ts]
```

## 📝 Documentation Checklist

When completing a component, ensure:

### Quick Reference (`component/README.md`)
- [ ] File structure documented
- [ ] Quick start example works
- [ ] Common operations covered (3-5 examples)
- [ ] Links to detailed docs
- [ ] Status badge (✅ Complete, 🔄 In Progress, ⏳ Planned)

### Detailed Guide (`docs/component.md`)
- [ ] Table of contents
- [ ] Overview section
- [ ] Architecture/design explanation
- [ ] Complete API reference
- [ ] Multiple usage examples
- [ ] Testing instructions
- [ ] Troubleshooting section
- [ ] Best practices
- [ ] All code examples tested and working

### Integration
- [ ] Updated `docs/README.md` index
- [ ] Updated main `README.md` if needed
- [ ] Added to project status tracking
- [ ] Cross-referenced from related docs

## 🎯 Documentation by Component Type

### For Code Components

**Must have:**
- Docstrings (Google style)
- Type hints
- Usage examples in docstring
- Quick reference in component folder
- Detailed guide in docs folder

**Example:**
```python
def process_ticket(
    ticket: Ticket,
    confidence_threshold: float = 0.8
) -> AgentState:
    """
    Process a support ticket through the agent workflow.
    
    Args:
        ticket: The ticket to process
        confidence_threshold: Minimum confidence for auto-resolution
        
    Returns:
        Final agent state after processing
        
    Example:
        >>> state = process_ticket(ticket, confidence_threshold=0.9)
        >>> if state.should_escalate:
        ...     escalate_to_human(state)
    """
```

### For Configuration

**Must have:**
- All settings documented
- Environment variable names
- Default values
- Validation rules
- Usage examples
- `.env.example` up to date

### For APIs

**Must have:**
- Endpoint documentation
- Request/response schemas
- Authentication requirements
- Example requests (curl, Python)
- Error codes and handling
- Rate limits

## 📊 Tracking Documentation Status

### Status Badges

Use these in `docs/README.md`:

- ✅ **Complete** - Fully documented, tested, ready
- 🔄 **In Progress** - Being documented
- ⏳ **Planned** - Not yet documented
- ⚠️ **Needs Update** - Code changed, docs stale

### Documentation Metrics

Track in `docs/README.md`:
```markdown
| Component | Status | Completeness | Last Updated |
|-----------|--------|--------------|--------------|
| Config    | ✅     | 100%         | 2024-12      |
| Models    | ✅     | 100%         | 2024-12      |
| Agents    | 🔄     | 40%          | 2024-12      |
```

## 🔄 Keeping Documentation Current

### When Code Changes

1. **Update inline docs** (docstrings, comments)
2. **Update quick reference** if APIs changed
3. **Update detailed guide** if behavior changed
4. **Update examples** if they broke
5. **Run validation** to catch errors

### Regular Maintenance

**Weekly:**
- Review open PRs for doc updates
- Check if examples still work

**Per Release:**
- Review all documentation
- Update version numbers
- Check all links work
- Regenerate API docs if automated

## 🎨 Documentation Style Guide

### Writing Style

**Do:**
- Use clear, simple language
- Write in present tense
- Use active voice
- Include code examples
- Show before/after for changes
- Use emoji for visual scanning (sparingly)

**Don't:**
- Use jargon without explanation
- Write walls of text
- Skip examples
- Assume knowledge
- Use future tense ("we will implement")

### Code Examples

**Always:**
- Test your examples
- Use realistic variable names
- Include imports
- Show output/results
- Handle errors properly

**Example:**
```python
# ✅ Good - Complete, tested example
from config import settings, get_prompt

# Load configuration
api_key = settings.llm.claude.api_key.get_secret_value()

# Get agent prompt
prompt = get_prompt("system_prompts.intake_agent")

# ❌ Bad - Incomplete, unclear
settings.stuff.thing  # What is this?
```

### Formatting

**Headers:**
```markdown
# H1 - Document title only
## H2 - Major sections
### H3 - Subsections
#### H4 - Rare, for very detailed breakdowns
```

**Code blocks:**
- Always specify language: ` ```python `, ` ```bash `
- Include context (imports, setup)
- Add comments for clarity

**Lists:**
- Use `-` for unordered lists
- Use `1.` for ordered lists
- Keep items parallel in structure

## 🚀 Going Forward

### For Each New Component

1. **Start with quick reference** - Create `component/README.md`
2. **Write as you code** - Add docstrings, comments
3. **Finish with detailed guide** - Create `docs/component.md`
4. **Update indexes** - Add to `docs/README.md`
5. **Cross-reference** - Link related docs
6. **Validate** - Test all examples

### Documentation Reviews

Before merging any PR:
- [ ] New code has docstrings
- [ ] Public APIs documented
- [ ] Examples included and tested
- [ ] Quick reference updated
- [ ] Detailed guide updated (if major change)
- [ ] Index updated

## 📚 Resources

**Good documentation examples:**
- [FastAPI Docs](https://fastapi.tiangolo.com/) - Excellent API docs
- [Stripe API Docs](https://stripe.com/docs/api) - Great reference docs
- [Django Docs](https://docs.djangoproject.com/) - Comprehensive guides

**Tools:**
- Markdown editors: Typora, VS Code
- Diagrams: Mermaid, draw.io
- API docs: Swagger/OpenAPI

## ✅ Summary

**Our documentation system:**
- ✅ Two-tier: Quick reference + Detailed guide
- ✅ Component-specific READMEs
- ✅ Centralized docs/ folder
- ✅ Examples tested and working
- ✅ Status tracking
- ✅ Updated with code

**For every component we complete:**
1. Create quick reference in component folder
2. Create detailed guide in docs folder
3. Update documentation index
4. Test all examples
5. Mark as complete (✅)

This ensures the project is always well-documented and easy to maintain!

---

**Status:** ✅ Active  
**Last Updated:** 2024-12  
**Owner:** Development Team
