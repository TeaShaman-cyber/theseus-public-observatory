-- Apply only after the schema, rollback-only tests and manual refresh pass.
select cron.schedule('observatory-journal-refresh', '*/15 * * * *',
                     'select observatory_sync.refresh()');
