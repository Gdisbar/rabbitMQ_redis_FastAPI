-- KEYS[1] = identity rl key   (rl:user:<id>  or  rl:ip:<ip>)
-- KEYS[2] = burst key         (rl:burst:global)
-- KEYS[3] = blocklist key     (jwt:blocklist:<jti>, or a placeholder if guest)
--
-- ARGV[1] = now_ms
-- ARGV[2] = window_ms          (per-identity window)
-- ARGV[3] = limit              (per-identity max requests in window)
-- ARGV[4] = burst_limit
-- ARGV[5] = burst_window_ms
-- ARGV[6] = has_jti            (0/1)
--
-- returns { allowed (0|1), count_or_code, reason_str }

local now_ms       = tonumber(ARGV[1])
local window_ms    = tonumber(ARGV[2])
local limit        = tonumber(ARGV[3])
local burst_limit  = tonumber(ARGV[4])
local burst_window = tonumber(ARGV[5])
local has_jti      = tonumber(ARGV[6])

-- 1) JWT blocklist check (revoked token)
if has_jti == 1 then
  if redis.call('EXISTS', KEYS[3]) == 1 then
    return {0, -1, 'blocked'}
  end
end

-- 2) Global burst cap (fixed window). Counts every attempt, allowed or not.
local burst = redis.call('INCR', KEYS[2])
if burst == 1 then
  redis.call('PEXPIRE', KEYS[2], burst_window)
end
if burst > burst_limit then
  return {0, burst, 'burst'}
end

-- 3) Per-identity sliding window
redis.call('ZREMRANGEBYSCORE', KEYS[1], 0, now_ms - window_ms)
local count = redis.call('ZCARD', KEYS[1])
if count >= limit then
  return {0, count, 'rate'}
end

redis.call('ZADD', KEYS[1], now_ms, now_ms)
redis.call('PEXPIRE', KEYS[1], window_ms)

return {1, count + 1, 'ok'}