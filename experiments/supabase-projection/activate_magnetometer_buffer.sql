-- Bounded noncommercial private pilot. Operator runs once; not a migration.
select cron.schedule(
  'observatory-magnetic-buffer',
  '17 */6 * * *',
  format($job$do $body$ begin
    if clock_timestamp() >= %L::timestamptz then
      perform cron.unschedule('observatory-magnetic-buffer');
    else
      perform observatory_sync.collect_magnetic_buffer();
    end if;
  end $body$;$job$,clock_timestamp()+interval '7 days')
);
