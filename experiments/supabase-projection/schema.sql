create table public.observatory_journal (
  journal_path text not null check (journal_path ~ '^data/[0-9]{4}-[0-9]{2}-[0-9]{2}/public-status[.]jsonl$'),
  journal_line integer not null check (journal_line > 0),
  line_sha256 text not null check (line_sha256 ~ '^[0-9a-f]{64}$'),
  source_commit text not null check (source_commit ~ '^[0-9a-f]{40}$'),
  receipt jsonb not null check (jsonb_typeof(receipt) = 'object' and receipt ? 'collected_at' and jsonb_typeof(receipt->'sources') = 'array'),
  primary key (journal_path, journal_line)
);
alter table public.observatory_journal enable row level security;
revoke all on public.observatory_journal from public, anon, authenticated, service_role;
grant select, insert on public.observatory_journal to service_role;

create view public.observatory_sources with (security_invoker = true) as
select j.journal_path, j.journal_line, j.line_sha256,
       (j.receipt->>'collected_at')::timestamptz as collected_at,
       s->>'id' as source_id, s->>'ok' as collector_ok,
       s#>>'{semantic,status}' as semantic_status,
       s as sensor
from public.observatory_journal j
cross join lateral jsonb_array_elements(j.receipt->'sources') s;

create view public.observatory_radar_points with (security_invoker = true) as
select s.journal_path, s.journal_line, s.collected_at, s.source_id,
       s.sensor#>>'{summary,provider}' as provider,
       s.sensor#>>'{summary,metric}' as metric,
       (s.sensor#>>'{summary,window_start}')::timestamptz as window_start,
       (s.sensor#>>'{summary,window_end}')::timestamptz as window_end,
       (p->>'measured_at')::timestamptz as measured_at,
       (p->>'value')::double precision as value
from public.observatory_sources s
cross join lateral jsonb_array_elements(
  case when jsonb_typeof(s.sensor#>'{summary,points}') = 'array'
       then s.sensor#>'{summary,points}' else '[]'::jsonb end
) p
where s.sensor->>'adapter' = 'cloudflare-radar-origins-v1'
  and s.collector_ok = 'true' and s.semantic_status = 'available'
  and s.sensor#>>'{summary,value_unit}' = 'window_max_fraction';

create view public.observatory_radar_correlations with (security_invoker = true) as
select a.journal_path, a.journal_line, a.collected_at, a.provider,
       a.window_start, a.window_end, count(*) as paired,
       max(a.measured_at) as latest_paired_at, corr(a.value,b.value) as pearson_r
from public.observatory_radar_points a
join public.observatory_radar_points b
  on (a.journal_path,a.journal_line,a.provider,a.window_start,a.window_end,a.measured_at)
   = (b.journal_path,b.journal_line,b.provider,b.window_start,b.window_end,b.measured_at)
where a.metric = 'REQUESTS' and b.metric = 'CONNECTION_FAILURES'
group by a.journal_path,a.journal_line,a.collected_at,a.provider,a.window_start,a.window_end;

revoke all on public.observatory_sources, public.observatory_radar_points, public.observatory_radar_correlations from public, anon, authenticated, service_role;
grant select on public.observatory_sources, public.observatory_radar_points, public.observatory_radar_correlations to service_role;
notify pgrst, 'reload schema';
