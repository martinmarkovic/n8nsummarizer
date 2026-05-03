# Documentation

Developer notes, changelogs, technical guides, and architecture documentation for Media SwissKnife.

## Contents

### Changelogs

| File | Description |
|------|-------------|
| `CHANGELOG_v6.3.md` | Version 6.3 changes and features |
| `CHANGELOG_v6.4.md` | Version 6.4 changes and features |

### Technical Guides

| File | Description |
|------|-------------|
| `ROADMAP.md` | Future development plans and priorities |
| `PO_TOKEN_ISSUE_RESOLUTION.md` | YouTube PO token issue resolution |
| `PO_TOKEN_QUICK_START.md` | Quick start guide for PO tokens |
| `SABR_STREAMING_FIX.md` | SABR streaming implementation details |
| `YOUTUBE_PO_TOKEN_GUIDE.md` | Comprehensive YouTube PO token guide |

### Architecture Documentation

| File | Description |
|------|-------------|
| `PHASE3_CHANGES_SUMMARY.md` | Phase 3 refactoring summary |
| `PHASE4_IMPLEMENTATION_SUMMARY.md` | Phase 4 architectural improvements |
| `CALLBACK_FIX_SUMMARY.md` | Callback scope issue resolution |
| `SETTINGS_ARCHITECTURE_DECISION.md` | SettingsManager architecture rationale |

## Subdirectories

### docs/browser_extension/

Contains documentation and resources for the browser extension component:
- Installation instructions
- Usage guides
- Troubleshooting

**See**: [docs/browser_extension/README.md](browser_extension/README.md)

## Documentation Standards

### Structure

All documentation files should follow:

```markdown
# Title

## Purpose
One paragraph summary

## Contents
Table of files/sections

## Detailed Sections
Organized information

## Examples (if applicable)
Code samples or screenshots

## References
Links to related documentation
```

### Style Guide

1. **Clear Headings**: Use hierarchical headings (##, ###, ####)
2. **Concise Language**: Get to the point quickly
3. **Code Examples**: Use fenced code blocks with syntax highlighting
4. **Cross-References**: Link to related documentation
5. **Version Information**: Include version numbers when relevant

## Adding New Documentation

To add new documentation:

1. **Choose Location**: Decide between root docs/ or subdirectory
2. **Follow Template**: Use standard structure
3. **Update Index**: Add to this README
4. **Link Related**: Reference from other relevant docs
5. **Review**: Ensure accuracy and clarity

## Documentation Workflow

1. **Write**: Create initial draft
2. **Review**: Technical accuracy check
3. **Test**: Verify instructions work
4. **Update**: Keep current with code changes
5. **Archive**: Move old versions to appropriate locations

## Issue Tracking

Documentation issues should be tracked in GitHub issues with:
- **Label**: `documentation`
- **Template**: Use documentation issue template
- **Priority**: Based on impact

## Future Documentation Needs

Areas needing documentation:
- Complete API reference
- Architecture decision records
- Migration guides between versions
- Troubleshooting guides
- Performance optimization guides