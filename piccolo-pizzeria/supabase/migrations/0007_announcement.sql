-- Stage 7: "Tonight at Piccolo" announcement — a single admin-toggled
-- banner, same shape as the existing ordering_paused/ordering_paused_message
-- pair on business_settings (one flag, one message, single-row table).
alter table business_settings
  add column announcement_active boolean not null default false,
  add column announcement_message text;

comment on column business_settings.announcement_active is 'Shows the "Tonight at Piccolo" banner storefront-wide when true. Renders nothing when false.';
comment on column business_settings.announcement_message is 'Banner copy, e.g. a tonight-only special or event. Ignored when announcement_active is false.';
