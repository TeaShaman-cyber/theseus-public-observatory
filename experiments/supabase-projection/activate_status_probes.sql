-- A bounded seven-day pilot. The job self-unschedules at expiry.
-- This script is a one-time operator action, not a replayable migration.
select cron.schedule(
 'observatory-status-probes',
 '*/5 * * * *',
 format($job$do $body$ begin
 if clock_timestamp() >= %L::timestamptz then
   perform cron.unschedule('observatory-status-probes');
 else
   perform observatory_sync.collect_status_pair();
 end if;
 end $body$;$job$,clock_timestamp()+interval '7 days'));
