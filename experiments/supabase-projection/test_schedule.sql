-- Rollback-only acceptance; no network and no durable fixture.
begin;
do $$
declare
  line text := '{"collected_at":"2099-01-01T00:00:00Z","sources":[]}';
  n integer;
begin
  n := observatory_sync.import_day('2099-01-01', repeat('a',40), line || E'\n');
  if n <> 1 then raise exception 'first import mismatch'; end if;
  n := observatory_sync.import_day('2099-01-01', repeat('b',40), line || E'\n');
  if n <> 0 then raise exception 'replay inserted'; end if;
  begin
    perform observatory_sync.import_day('2099-01-01', repeat('b',40),
      replace(line,'00:00:00','00:01:00') || E'\n');
    raise exception 'conflict not detected';
  exception when sqlstate '23505' then null;
  end;
  begin
    perform observatory_sync.import_day('2099-01-01', repeat('b',40), '');
    raise exception 'empty file accepted';
  exception when sqlstate '22023' then null;
  end;
  if (select count(*) from public.observatory_journal where journal_path='data/2099-01-01/public-status.jsonl') <> 1 then
    raise exception 'unexpected fixture rows';
  end if;
end
$$;
rollback;
