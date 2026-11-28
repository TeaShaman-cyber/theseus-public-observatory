create schema observatory_sync;
revoke all on schema observatory_sync from public, anon, authenticated, service_role;
create extension http with schema observatory_sync;

create table observatory_sync.runs (
  started_at timestamptz primary key,
  finished_at timestamptz not null,
  source_commit text,
  inserted integer not null check (inserted >= 0),
  status text not null check (status in ('verified','error')),
  step text not null,
  error_code text
);
alter table observatory_sync.runs enable row level security;
revoke all on observatory_sync.runs from public, anon, authenticated, service_role;

create function observatory_sync.import_day(day_text text, commit_sha text, journal_text text)
returns integer language plpgsql security invoker set search_path = '' as $$
declare
  path text;
  row_text text;
  line_no bigint;
  parsed jsonb;
  hash text;
  added integer := 0;
  affected integer;
  seen integer := 0;
begin
  if day_text is null or day_text !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
     or commit_sha is null or commit_sha !~ '^[0-9a-f]{40}$'
     or journal_text is null or octet_length(journal_text) not between 1 and 8388608 then
    raise exception using errcode='22023', message='invalid journal input';
  end if;
  path := 'data/' || day_text || '/public-status.jsonl';
  for row_text, line_no in
    select value, ordinality
    from regexp_split_to_table(regexp_replace(journal_text,E'\n$',''),E'\n')
      with ordinality as t(value,ordinality)
  loop
    if row_text = '' or position(E'\r' in row_text) > 0 then
      raise exception using errcode='22023', message='invalid journal line';
    end if;
    parsed := row_text::jsonb;
    if jsonb_typeof(parsed) is distinct from 'object'
       or jsonb_typeof(parsed->'sources') is distinct from 'array'
       or (parsed->>'collected_at') is null then
      raise exception using errcode='22023', message='invalid receipt';
    end if;
    perform (parsed->>'collected_at')::timestamptz;
    hash := encode(sha256(convert_to(row_text,'UTF8')),'hex');
    insert into public.observatory_journal(journal_path,journal_line,line_sha256,source_commit,receipt)
      values(path,line_no,hash,commit_sha,parsed)
      on conflict (journal_path,journal_line) do nothing;
    get diagnostics affected = row_count;
    added := added + affected;
    if not exists(select 1 from public.observatory_journal j
      where j.journal_path=path and j.journal_line=line_no
      and j.line_sha256=hash and j.receipt=parsed) then
      raise exception using errcode='23505',message='immutable journal conflict';
    end if;
    seen := seen + 1;
  end loop;
  if seen=0 or exists(select 1 from public.observatory_journal j where j.journal_path=path and j.journal_line>seen) then
    raise exception using errcode='22023',message='empty or truncated journal';
  end if;
  return added;
end;
$$;

create function observatory_sync.refresh()
returns void language plpgsql security invoker set search_path = '' as $$
declare
  started timestamptz := clock_timestamp();
  stage text := 'ref';
  sha text;
  response observatory_sync.http_response;
  day_text text;
  inserted_count integer := 0;
begin
  if not pg_try_advisory_xact_lock(351128,1) then return; end if;
  begin
    perform set_config('http.curlopt_timeout_ms','10000',true);
    perform set_config('http.curlopt_connecttimeout_ms','3000',true);
    perform set_config('http.curlopt_followlocation','0',true);
    select * into response from observatory_sync.http((
      'GET','https://api.github.com/repos/TeaShaman-cyber/theseus-public-observatory/git/ref/heads/main',
      array[observatory_sync.http_header('User-Agent','Theseus-Observatory-Sync'),observatory_sync.http_header('Accept','application/vnd.github+json')],
      null,null)::observatory_sync.http_request);
    if response.status is distinct from 200 or octet_length(response.content)>65536 then
      raise exception using errcode='22023',message='invalid Git reference response';
    end if;
    sha := response.content::jsonb#>>'{object,sha}';
    if sha is null or sha !~ '^[0-9a-f]{40}$' then
      raise exception using errcode='22023',message='invalid Git reference';
    end if;
    for day_text in select to_char((started at time zone 'UTC')::date-i,'YYYY-MM-DD') from generate_series(1,0,-1) i
    loop
      stage := 'day:' || day_text;
      select * into response from observatory_sync.http_get(
        'https://raw.githubusercontent.com/TeaShaman-cyber/theseus-public-observatory/' || sha || '/data/' || day_text || '/public-status.jsonl');
      if response.status is distinct from 200 then
        raise exception using errcode='22023',message='journal fetch failed';
      end if;
      inserted_count := inserted_count + observatory_sync.import_day(day_text,sha,response.content);
    end loop;
    insert into observatory_sync.runs values(started,clock_timestamp(),sha,inserted_count,'verified','complete',null);
  exception when others then
    -- The exception block rolls back both day's imports. Keep only a bounded diagnostic.
    insert into observatory_sync.runs values(started,clock_timestamp(),sha,0,'error',stage,sqlstate);
  end;
end;
$$;

revoke execute on function observatory_sync.import_day(text,text,text), observatory_sync.refresh() from public, anon, authenticated, service_role;
