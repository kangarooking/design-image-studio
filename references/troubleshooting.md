# Troubleshooting Guide

## Error Classification

### Authentication Errors (401/403)

**Symptom**: `Unauthorized` or `Forbidden`

**Causes & Fixes**:
- `ARK_API_KEY` not set → Export the environment variable:
  ```bash
  export ARK_API_KEY="your-api-key-here"
  ```
- Invalid/expired key → Generate a new key at:
  https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
- Wrong region → Ensure you're using `ark.cn-beijing.volces.com`

**Retry**: No. Fix the key and try again.

---

### Rate Limiting (429)

**Symptom**: `Too Many Requests` or `Rate limit exceeded`

**Causes & Fixes**:
- IPM limit (500 images/minute) exceeded → Wait 60 seconds
- RPM limit exceeded → Check your account's RPM quota in the console

**Retry**: Yes, automatic with exponential backoff. The script handles this.

---

### Invalid Request (400)

**Symptom**: `Bad Request` or `Invalid parameter`

**Common causes & fixes**:

| Cause | Fix |
|---|---|
| Unsupported resolution for model | Check `references/models.md` for valid resolution/model combos |
| Invalid image URL | Ensure URLs are publicly accessible |
| Image too large | Reduce to < 10MB per image |
| Too many images | Max 14 reference images, total input+output ≤ 15 |
| Invalid size format | Use preset (`2K`) or exact pixels (`2048x2048`) |
| Mixed size methods | Don't mix preset and pixel formats |
| Aspect ratio out of range | Keep between 1:16 and 16:1 |
| Prompt too long | Keep under ~300 Chinese chars / ~600 English words |

**Retry**: No. Fix the parameter and try again.

---

### Content Policy Violation

**Symptom**: Error mentioning "content", "safety", or "policy"

**Causes**: Prompt or reference image triggered safety filters.

**Fix**:
1. Review the prompt for sensitive content (violence, explicit material, etc.)
2. If using reference images, ensure they don't contain policy-violating content
3. Rephrase the prompt to avoid flagged terms
4. Try a more abstract or metaphorical description instead

**Retry**: No. Revise the prompt.

---

### Server Errors (5xx)

**Symptom**: `Internal Server Error`, `Service Unavailable`, `Gateway Timeout`

**Causes**: Temporary Volcengine platform issues.

**Retry**: Yes, automatic with exponential backoff. If persistent:
- Check Volcengine status page
- Try a different model as fallback
- Wait a few minutes and retry

---

### Network/Timeout Errors

**Symptom**: `ConnectionError`, `Timeout`, `Connection reset`

**Causes**: Network issues between client and API server.

**Retry**: Yes, automatic with exponential backoff.

**Workarounds**:
- Use `b64_json` response format to avoid download timeouts
- Reduce image size to speed up generation
- Check network connectivity and proxy settings

---

### SDK Installation Issues

**Symptom**: `ModuleNotFoundError: No module named 'volcenginesdkarkruntime'`

**Fix**:
```bash
pip install 'volcengine-python-sdk[ark]'
```

For version issues:
```bash
pip install --upgrade 'volcengine-python-sdk[ark]'
```

---

### Output Issues

| Problem | Possible Cause | Fix |
|---|---|---|
| Blurry/low quality | Resolution too low | Use 2K or higher |
| Wrong aspect ratio | Size mismatch | Specify exact pixels (e.g., `2048x2048`) |
| Unwanted watermark | `--watermark` flag | Remove the flag (default is no watermark) |
| JPEG artifacts | JPEG format | Use `--output-format png` (5.0/5.0 lite only) |
| URL expired | 24-hour retention | Download images promptly |
| Color shift | JPEG compression | Use PNG format |
| Content not matching prompt | Prompt too vague | Add specific details, style, composition |

---

### Retry Strategy Reference

```
Attempt 1: Immediate
Attempt 2: ~1s + jitter     (default)
Attempt 3: ~2s + jitter     (default)
Attempt 4: ~4s + jitter     (if max_retries > 3)
  ↓ on final failure
Fallback model (if configured)
  ↓ retry cycle restarts on fallback
  ↓ on exhaustion
Report error to user
```
