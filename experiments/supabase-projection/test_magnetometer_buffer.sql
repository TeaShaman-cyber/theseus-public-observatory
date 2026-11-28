begin;
do $$
declare
  t timestamptz := '2000-01-01 00:00Z';
  a timestamptz := '2000-01-02 00:00Z';
  b timestamptz := '2000-01-05 00:00Z';
begin
  perform observatory_sync.record_magnetic_capture('irt',t,a,200,'first',null);
  perform observatory_sync.record_magnetic_capture('irt',t,a+interval '1 second',200,'first',null);
  perform observatory_sync.record_magnetic_capture('irt',t,b,200,'revised',null);
  perform observatory_sync.record_magnetic_capture('irt',t,b+interval '1 second',null,null,'57014');
  if (select count(*) from observatory_sync.magnetic_attempts where window_start=t) <> 4 then raise exception 'attempt lost'; end if;
  if (select count(distinct payload_sha256) from observatory_sync.magnetic_attempts where window_start=t) <> 2 then raise exception 'revision lost or duplicate bytes'; end if;
  if (select count(*) from observatory_sync.magnetic_attempts where window_start=t and outcome='transport_error' and payload_sha256 is null) <> 1 then raise exception 'failure lost'; end if;
  begin
    update observatory_sync.magnetic_attempts set outcome='received_unvalidated' where window_start=t;
    raise exception 'mutation accepted';
  exception when insufficient_privilege then null;
  end;
  begin
    delete from observatory_sync.magnetic_payloads where body='first';
    raise exception 'delete accepted';
  exception when insufficient_privilege then null;
  end;
  if has_table_privilege('service_role','observatory_sync.magnetic_payloads','SELECT') or has_table_privilege('anon','observatory_sync.magnetic_attempts','SELECT') then raise exception 'unexpected grants'; end if;
end $$;
rollback;
