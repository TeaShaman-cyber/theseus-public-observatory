create view public.observatory_status_series with (security_invoker=true) as
select collected_at as sample_at, 'journal_batch_time'::text as timestamp_kind,
       'github-journal'::text as collector, source_id,
       case when collector_ok='true' and semantic_status='available'
          and sensor#>>'{summary,indicator}' in ('none','minor','major','critical','maintenance')
            then 'available' else 'unknown' end as outcome,
       case when collector_ok='true' and semantic_status='available'
          and sensor#>>'{summary,indicator}' in ('none','minor','major','critical','maintenance')
            then sensor#>>'{summary,indicator}' end as indicator,
       case when jsonb_typeof(sensor->'http_status')='number'
            then (sensor->>'http_status')::integer end as http_status,
       case when jsonb_typeof(sensor->'latency_ms')='number'
            then (sensor->>'latency_ms')::integer end as latency_ms
from public.observatory_sources
where source_id in ('openai_status','github_status')
union all
select observed_at,'request_end',collector,source_id,outcome,indicator,http_status,latency_ms
from public.observatory_status_probes;
revoke all on public.observatory_status_series from public,anon,authenticated,service_role;
grant select on public.observatory_status_series to service_role;
notify pgrst, 'reload schema';
