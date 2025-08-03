# Grok4 Rollout and Rollback Plan

## Overview
This document outlines the procedures for rolling out Grok4 support in the Zen MCP Server and rolling back if issues arise.

## Rollout Strategy

### Phase 1: Initial Deployment (Low Risk)
1. **Deploy code changes** with Grok4 support
   - Grok4 is added as a new model alongside existing Grok3
   - No changes to default behavior (grok alias still points to grok-3)
   - Backward compatibility fully preserved

2. **Testing in production**
   - Users can explicitly request `grok-4` or `grok4`
   - Monitor logs for any errors or issues
   - Collect feedback from early adopters

### Phase 2: Gradual Migration (Medium Risk)
1. **Enable GROK4_DEFAULT for select users**
   - Set `GROK4_DEFAULT=true` in .env for pilot users
   - The `grok` alias now resolves to `grok-4`
   - Users can still explicitly request `grok-3` if needed

2. **Monitor and adjust**
   - Track API errors and parameter conversion issues
   - Monitor token usage (256K vs 131K context)
   - Gather performance metrics

### Phase 3: Full Migration (Higher Risk)
1. **Update default behavior**
   - Change the default alias mapping in code
   - Update documentation to reflect Grok4 as primary
   - Deprecation notice for Grok3-specific features

## Rollback Procedures

### Quick Rollback (Environment Variable)
If issues arise during Phase 2:
```bash
# In .env file
GROK4_DEFAULT=false
```
This immediately reverts `grok` alias to point to `grok-3`.

### Code-Level Rollback
If critical issues with Grok4 implementation:

1. **Option A: Disable Grok4** (Minimal change)
   ```python
   # In xai.py, comment out grok-4 from SUPPORTED_MODELS
   # "grok-4": ModelCapabilities(...),  # DISABLED
   ```

2. **Option B: Full Revert** (Complete rollback)
   ```bash
   # Revert the Grok4 implementation commit
   git revert <commit-hash>
   ```

### Emergency Mitigation
For immediate production issues:

1. **Block Grok4 via restrictions**
   ```bash
   # In .env
   XAI_ALLOWED_MODELS=grok-3,grok-3-fast
   ```
   This prevents any Grok4 usage while keeping code intact.

## Monitoring Checklist

### Key Metrics to Track
- [ ] API error rates for grok-4 model calls
- [ ] Parameter conversion success (max_completion_tokens)
- [ ] Token usage patterns (context window utilization)
- [ ] Response quality and reasoning performance
- [ ] Cost implications (if different pricing)

### Log Monitoring
```bash
# Monitor Grok4 specific errors
grep "grok-4" logs/mcp_server.log | grep ERROR

# Check parameter removal logs
grep "Removing unsupported parameter" logs/mcp_server.log

# Track model resolution
grep "_resolve_model_name.*grok" logs/mcp_server.log
```

## Testing Procedures

### Pre-Rollout Testing
1. Run unit tests: `python -m pytest tests/test_grok4_provider.py -v`
2. Run integration tests: `./run_integration_tests.sh`
3. Test model resolution with different GROK4_DEFAULT settings
4. Verify listmodels output shows Grok4 correctly

### Post-Rollout Validation
1. Test explicit grok-4 requests
2. Verify parameter conversion for reasoning models
3. Test context window limits (256K tokens)
4. Validate JSON mode and tool use capabilities
5. Check thinking mode support

## Risk Matrix

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| API parameter incompatibility | Medium | High | Parameter conversion layer, extensive testing |
| Performance degradation | Low | Medium | Gradual rollout, monitoring |
| Cost increase | Medium | Low | Usage monitoring, user communication |
| Breaking changes for existing code | Very Low | High | Backward compatibility, aliasing |
| Model behavior differences | Medium | Medium | Documentation, user education |

## Communication Plan

### Internal Team
- [ ] Notify development team of rollout schedule
- [ ] Share monitoring dashboard access
- [ ] Document known limitations

### End Users
- [ ] Release notes highlighting new Grok4 capabilities
- [ ] Migration guide for advanced features
- [ ] FAQ for common issues

## Success Criteria

### Phase 1 Success
- No increase in error rates
- Successful explicit grok-4 requests
- Positive early adopter feedback

### Phase 2 Success  
- <1% error rate with GROK4_DEFAULT=true
- Successful parameter conversions
- No performance regressions

### Full Migration Success
- Complete transition to Grok4 as default
- All tests passing
- User satisfaction maintained or improved