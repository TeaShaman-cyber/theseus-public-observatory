-- Private, bounded, noncommercial capture evidence. Not definitive science data.
begin;
create table observatory_sync.magnetic_payloads (
  sha256 text primary key,
  body text not null check (octet_length(body) between 1 and 131072),
  check (sha256 = encode(sha256(convert_to(body,'UTF8')),'hex'))
);
create table observatory_sync.magnetic_attempts (
  station text not null check(station in ('irt','kak')),
  window_start timestamptz not null,
  captured_at timestamptz not null check(captured_at >= window_start+interval '6 hours'),
  http_status integer check(http_status between 100 and 599),
  outcome text not null check(outcome in ('received_unvalidated','http_error','invalid_size','transport_error')),
  payload_sha256 text references observatory_sync.magnetic_payloads(sha256),
  error_code text,
  primary key(station,window_start,captured_at),
  check (window_start=date_bin(interval '6 hours',window_start,timestamptz '2000-01-01 00:00Z')),
  check (outcome <> 'received_unvalidated' or (http_status=200 and payload_sha256 is not null)),
  check (outcome <> 'transport_error' or (http_status is null and payload_sha256 is null and error_code is not null))
);
alter table observatory_sync.magnetic_payloads enable row level security;
alter table observatory_sync.magnetic_attempts enable row level security;
revoke all on observatory_sync.magnetic_payloads,observatory_sync.magnetic_attempts from public,anon,authenticated,service_role;

create function observatory_sync.reject_magnetic_mutation()
returns trigger language plpgsql security invoker set search_path='' as $$
begin
  raise exception using errcode='42501',message='append-only magnetic capture evidence';
end $$;
create trigger magnetic_payloads_append_only before update or delete or truncate on observatory_sync.magnetic_payloads
for each statement execute function observatory_sync.reject_magnetic_mutation();
create trigger magnetic_attempts_append_only before update or delete or truncate on observatory_sync.magnetic_attempts
for each statement execute function observatory_sync.reject_magnetic_mutation();

create function observatory_sync.record_magnetic_capture(
  st text, w timestamptz, observed timestamptz, code integer, contents text, err text
) returns void language plpgsql security invoker set search_path='' as $$
declare
  digest text;
  verdict text;
begin
  if code is null then
    verdict := 'transport_error';
  else
    if octet_length(contents) between 1 and 131072 then
      digest := encode(sha256(convert_to(contents,'UTF8')),'hex');
      insert into observatory_sync.magnetic_payloads(sha256,body)
        values(digest,contents) on conflict(sha256) do nothing;
      if not exists(select 1 from observatory_sync.magnetic_payloads where sha256=digest and body=contents) then
        raise exception 'payload identity conflict';
      end if;
    end if;
    verdict := case when code <> 200 then 'http_error'
                    when digest is null then 'invalid_size'
                    else 'received_unvalidated' end;
  end if;
  insert into observatory_sync.magnetic_attempts(station,window_start,captured_at,http_status,outcome,payload_sha256,error_code)
    values(st,w,observed,code,verdict,digest,err);
end $$;

create function observatory_sync.collect_magnetic_buffer()
returns void language plpgsql security invoker set search_path='' as $$
declare
  cutoff timestamptz := date_bin(interval '6 hours',clock_timestamp(),timestamptz '2000-01-01 00:00Z');
  w timestamptz;
  st text;
  url text;
  response observatory_sync.http_response;
  code integer;
  contents text;
  err text;
begin
  if not pg_try_advisory_xact_lock(351128,3) then return; end if;
  perform set_config('http.curlopt_timeout_ms','10000',true);
  perform set_config('http.curlopt_connecttimeout_ms','3000',true);
  perform set_config('http.curlopt_followlocation','0',true);
  foreach st in array array['irt','kak'] loop
    foreach w in array array[cutoff-interval '6 hours',cutoff-interval '78 hours'] loop
      url := 'https://imag-data.bgs.ac.uk/GIN_V1/hapi/data?id='||st||
        '%2Fbest-avail%2FPT1M%2Fxyzf&time.min='||
        to_char(w at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS"Z"')||
        '&time.max='||to_char((w+interval '6 hours') at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS"Z"')||
        '&format=csv&include=header';
      code:=null; contents:=null; err:=null;
      begin
        select * into response from observatory_sync.http_get(url);
        code:=response.status; contents:=response.content;
      exception when others then
        err:=sqlstate;
      end;
      perform observatory_sync.record_magnetic_capture(st,w,clock_timestamp(),code,contents,err);
    end loop;
  end loop;
end $$;
revoke execute on function observatory_sync.reject_magnetic_mutation(),observatory_sync.record_magnetic_capture(text,timestamptz,timestamptz,integer,text,text),observatory_sync.collect_magnetic_buffer() from public,anon,authenticated,service_role;
commit;
