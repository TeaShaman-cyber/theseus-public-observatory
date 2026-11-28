-- Offline fixture tests (no external requests), run in rollback-only transaction.
begin;
do $$
begin
 if observatory_sync.status_indicator('{"status":{"indicator":"none"}}') is distinct from 'none' then
   raise exception 'operational response rejected';
 end if;
 if observatory_sync.status_indicator('{"status":{"indicator":"major"}}') is distinct from 'major' then
   raise exception 'degraded response rejected';
 end if;
 if observatory_sync.status_indicator('{"status":{"indicator":"future-unknown"}}') is not null
    or observatory_sync.status_indicator('{"status":{"description":"All Systems Operational"}}') is not null
    or observatory_sync.status_indicator('not JSON') is not null
    or observatory_sync.status_indicator('{"status":{"indicator":42}}') is not null then
   raise exception 'unknown or invalid data incorrectly accepted';
 end if;
 if has_table_privilege('anon','public.observatory_status_probes','SELECT')
    or has_table_privilege('authenticated','public.observatory_status_probes','SELECT')
    or has_table_privilege('service_role','public.observatory_status_probes','INSERT')
    or not has_table_privilege('service_role','public.observatory_status_probes','SELECT')
    or has_function_privilege('service_role','observatory_sync.collect_status_pair()','EXECUTE') then
   raise exception 'unexpected grants';
 end if;
end
$$;
rollback;
