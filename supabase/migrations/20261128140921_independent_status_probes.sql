-- Independent pilot, not a replacement for the canonical Git archive.
create table public.observatory_status_probes (
  run_started_at timestamptz not null,
  source_id text not null check (source_id in ('openai_status','github_status')),
  observed_at timestamptz not null check (observed_at >= run_started_at),
  collector text not null default 'supabase-fra-http-v1' check (collector='supabase-fra-http-v1'),
  latency_ms integer not null check (latency_ms >= 0),
  http_status integer check (http_status between 100 and 599),
  outcome text not null check (outcome in ('available','transport_error','http_error','invalid_payload')),
  indicator text check (indicator in ('none','minor','major','critical','maintenance')),
  payload_sha256 text check (payload_sha256 ~ '^[0-9a-f]{64}$'),
  error_code text,
  primary key (run_started_at,source_id),
  check ((outcome='available') = (indicator is not null)),
  check (outcome<>'available' or (http_status=200 and payload_sha256 is not null)),
  check (outcome<>'transport_error' or http_status is null)
);
alter table public.observatory_status_probes enable row level security;
revoke all on public.observatory_status_probes from public, anon, authenticated, service_role;
grant select on public.observatory_status_probes to service_role;

create function observatory_sync.status_indicator(body text)
returns text language plpgsql immutable security invoker set search_path = '' as $$
declare
  value text;
begin
  if body is null or octet_length(body) not between 1 and 1048576 then
    return null;
  end if;
  value := body::jsonb#>>'{status,indicator}';
  if value in ('none','minor','major','critical','maintenance') then
    return value;
  end if;
  return null;
exception when invalid_text_representation then
  return null;
end;
$$;

create function observatory_sync.collect_status_pair()
returns void language plpgsql security invoker set search_path = '' as $$
declare
  run_time timestamptz := clock_timestamp();
  started timestamptz;
  finished timestamptz;
  src record;
  response observatory_sync.http_response;
  status_code integer;
  state text;
  ind text;
  hash text;
  failure text;
begin
  if not pg_try_advisory_xact_lock(351128,2) then return; end if;
  perform set_config('http.curlopt_timeout_ms','8000',true);
  perform set_config('http.curlopt_connecttimeout_ms','3000',true);
  perform set_config('http.curlopt_followlocation','0',true);
  for src in select * from (values
    ('openai_status','https://status.openai.com/api/v2/status.json'),
    ('github_status','https://www.githubstatus.com/api/v2/summary.json')
  ) as s(id,url)
  loop
    started := clock_timestamp();
    status_code := null; ind := null; hash := null; failure := null;
    begin
      select * into response from observatory_sync.http_get(src.url);
      finished := clock_timestamp();
      status_code := response.status;
      if octet_length(response.content) between 1 and 1048576 then
        hash := encode(sha256(convert_to(response.content,'UTF8')),'hex');
      end if;
      if status_code is distinct from 200 then
        state := 'http_error';
      else
        ind := observatory_sync.status_indicator(response.content);
        state := case when ind is null then 'invalid_payload' else 'available' end;
      end if;
    exception when others then
      finished := clock_timestamp();
      state := 'transport_error'; failure := sqlstate;
      status_code := null; ind := null; hash := null;
    end;
    insert into public.observatory_status_probes
      (run_started_at,source_id,observed_at,latency_ms,http_status,outcome,indicator,payload_sha256,error_code)
    values(run_time,src.id,finished,
      greatest(0,round(extract(epoch from finished-started)*1000)::integer),
      status_code,state,ind,hash,failure);
  end loop;
end;
$$;

revoke execute on function observatory_sync.status_indicator(text), observatory_sync.collect_status_pair() from public, anon, authenticated, service_role;
notify pgrst, 'reload schema';
