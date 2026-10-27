-- Initial PollingBrain schema. Already applied to the connected project.
-- For disaster recovery into a new empty project; not an idempotent migration.

create schema if not exists pollingbrain_private;
revoke all on schema pollingbrain_private from public, anon, authenticated;
create extension if not exists http with schema extensions;
create extension if not exists pg_cron;

create table public.data_sources (
 id text primary key, publisher text not null, category text not null,
 source_url text, status text not null default 'identified', caution text,
 created_at timestamptz not null default now()
);
create table public.source_snapshots (
 records_sha256 text primary key check(records_sha256 ~ '^[0-9a-f]{64}$'),
 source_id text not null references public.data_sources(id),
 retrieved_at timestamptz not null, imported_at timestamptz not null default now(),
 record_count integer not null check(record_count > 0),
 archive_sha256 text not null, source_url text not null,
 ballot_qualification_verified boolean not null default false check(not ballot_qualification_verified)
);
create index on public.source_snapshots(source_id, retrieved_at desc);
create table public.candidate_filings (
 snapshot_hash text not null references public.source_snapshots(records_sha256),
 fec_id text not null, name text not null, party text not null,
 election_year integer not null check(election_year=2026), state text not null,
 office text not null check(office in ('H','S')), district text not null,
 incumbency text not null, fec_status text not null,
 quality_flags text[] generated always as (case when name='' then array['missing_name'] else array[]::text[] end) stored,
 primary key(snapshot_hash,fec_id)
);
create index on public.candidate_filings(state,office);
create table public.collection_status (
 dataset text primary key, source_id text not null references public.data_sources(id),
 latest_snapshot_hash text references public.source_snapshots(records_sha256),
 last_source_check_at timestamptz, last_database_sync_at timestamptz,
 record_count integer not null default 0, status text not null default 'pending'
);
create table pollingbrain_private.collection_runs (
 id bigint generated always as identity primary key, dataset text not null,
 started_at timestamptz not null default now(), finished_at timestamptz,
 success boolean, error_message text
);
create table public.polls (
 id uuid primary key default gen_random_uuid(), source_id text not null references public.data_sources(id),
 original_release_url text not null, external_poll_id text,
 race_id text not null, pollster text not null, sponsor text,
 field_start date not null, field_end date not null check(field_end >= field_start),
 sample_size integer check(sample_size > 0), population text, method text,
 results jsonb not null check(jsonb_typeof(results)='array'),
 retrieved_at timestamptz not null default now(),
 review_status text not null default 'pending' check(review_status in ('pending','verified','rejected')),
 content_hash text not null unique, published_on date, evidence jsonb not null default '{}'::jsonb, review_notes text
);
create index on public.polls(race_id,field_end desc);
create index on public.polls(source_id);
create table public.election_results (
 id uuid primary key default gen_random_uuid(), source_id text not null references public.data_sources(id),
 source_url text not null, election_date date not null, race_id text not null,
 geography_id text not null, candidate_name text not null, party text,
 votes bigint not null check(votes >= 0), certified boolean not null default false,
 retrieved_at timestamptz not null default now(),
 review_status text not null default 'pending' check(review_status in ('pending','verified','rejected')),
 content_hash text not null unique
);
create index on public.election_results(race_id,election_date);
create index on public.election_results(source_id);
create table public.news_events (
 id uuid primary key default gen_random_uuid(), source_id text not null references public.data_sources(id),
 source_url text not null, headline text not null, published_at timestamptz not null,
 retrieved_at timestamptz not null default now(), claims jsonb not null default '[]',
 affected_races text[] not null default '{}',
 review_status text not null default 'pending' check(review_status in ('pending','verified','rejected')),
 content_hash text not null unique
);
create index on public.news_events(published_at desc);
create index on public.news_events(source_id);
create table public.forecast_versions (
 id uuid primary key default gen_random_uuid(), race_id text not null, model_version text not null,
 as_of timestamptz not null, created_at timestamptz not null default now(),
 probabilities jsonb not null, uncertainty jsonb not null,
 input_references jsonb not null, backtest_reference text,
 publication_status text not null default 'draft' check(publication_status in ('draft','published','withdrawn')),
 unique(race_id,model_version,as_of)
);

do $block$
declare t text;
begin
 foreach t in array array['data_sources','source_snapshots','candidate_filings','collection_status','polls','election_results','news_events','forecast_versions'] loop
 execute format('alter table public.%I enable row level security',t);
 execute format('revoke all on public.%I from anon, authenticated',t);
 execute format('grant select on public.%I to anon, authenticated',t);
 execute format('grant select,insert,update,delete on public.%I to service_role',t);
 end loop;
end $block$;
create policy public_sources on public.data_sources for select to anon,authenticated using(true);
create policy public_snapshots on public.source_snapshots for select to anon,authenticated using(true);
create policy public_filings on public.candidate_filings for select to anon,authenticated using(true);
create policy public_collection_status on public.collection_status for select to anon,authenticated using(true);
create policy verified_polls on public.polls for select to anon,authenticated using(review_status='verified');
create policy verified_results on public.election_results for select to anon,authenticated using(review_status='verified');
create policy verified_news on public.news_events for select to anon,authenticated using(review_status='verified');
create policy published_forecasts on public.forecast_versions for select to anon,authenticated using(publication_status='published');
alter table pollingbrain_private.collection_runs enable row level security;

create function pollingbrain_private.sync_fec_from_archive() returns jsonb
language plpgsql security invoker set search_path='' as $fn$
declare
 response extensions.http_response; manifest_response extensions.http_response;
 payload jsonb; manifest jsonb; digest text; canonical_records text;
 n integer; distinct_n integer; snapshot_time timestamptz; source_check timestamptz; run_id bigint;
begin
 if not pg_try_advisory_xact_lock(260027) then
  return jsonb_build_object('status','already_running');
 end if;
 insert into pollingbrain_private.collection_runs(dataset) values('fec_candidate_filings_2026') returning id into run_id;
 begin
  perform extensions.http_set_curlopt('CURLOPT_TIMEOUT_MS','20000');
  select * into response from extensions.http_get('https://raw.githubusercontent.com/zevibambi/PollingBrain/main/public/data/fec_candidate_filings_2026.json');
  if response.status <> 200 or octet_length(response.content) > 10000000 then raise exception 'Source snapshot HTTP or size check failed'; end if;
  payload := response.content::jsonb;
  if payload->>'dataset' is distinct from 'fec_candidate_filings_2026'
   or payload->'ballot_qualification_verified' is distinct from 'false'::jsonb
   or payload#>>'{source,url}' is distinct from 'https://www.fec.gov/files/bulk-downloads/2026/cn26.zip'
   or jsonb_typeof(payload->'records') is distinct from 'array'
  then raise exception 'Snapshot identity or trust level invalid'; end if;
  n:=jsonb_array_length(payload->'records');
  if n < 1 or n <> (payload->>'record_count')::integer then raise exception 'Record count invalid'; end if;
  select count(distinct item->>'fec_id') into distinct_n from jsonb_array_elements(payload->'records') item;
  if distinct_n <> n then raise exception 'Duplicate or missing candidate IDs'; end if;
  if exists(select 1 from jsonb_array_elements(payload->'records') item where
   item->>'fec_id' !~ '^[HS][0-9A-Z]{8}$' or item->>'election_year' is distinct from '2026'
   or item->>'office' not in ('H','S')
   or (select count(*) from jsonb_object_keys(item)) <> 9
   or not item ?& array['fec_id','name','party','election_year','state','office','district','incumbency','fec_status']
  ) then raise exception 'Candidate record validation failed'; end if;
  select '['||string_agg('{'||(select string_agg(to_jsonb(key)::text||':'||value::text,',' order by key collate "C") from jsonb_each(item))||'}',',' order by position)||']'
   into canonical_records from jsonb_array_elements(payload->'records') with ordinality as records(item,position);
  digest:=encode(extensions.digest(convert_to(canonical_records,'UTF8'),'sha256'),'hex');
  if digest is distinct from payload->>'records_sha256' then raise exception 'Snapshot content hash mismatch'; end if;
  snapshot_time:=(payload->>'retrieved_at')::timestamptz;
  select * into manifest_response from extensions.http_get('https://raw.githubusercontent.com/zevibambi/PollingBrain/main/public/data/collection_status.json');
  if manifest_response.status <> 200 then raise exception 'Collection manifest unavailable'; end if;
  manifest:=manifest_response.content::jsonb#>'{datasets,fec_candidate_filings_2026}';
  if manifest->>'records_sha256' is distinct from digest then raise exception 'Manifest and snapshot disagree'; end if;
  source_check:=(manifest->>'last_successful_check_at')::timestamptz;
  if snapshot_time is null or source_check is null or source_check < snapshot_time or source_check > now()+interval '5 minutes' then raise exception 'Source timestamps invalid'; end if;
  insert into public.source_snapshots(records_sha256,source_id,retrieved_at,record_count,archive_sha256,source_url)
   values(digest,'fec-candidate-master-2026',snapshot_time,n,payload->>'source_archive_sha256',payload#>>'{source,url}') on conflict do nothing;
  insert into public.candidate_filings(snapshot_hash,fec_id,name,party,election_year,state,office,district,incumbency,fec_status)
   select digest,item->>'fec_id',item->>'name',item->>'party',2026,item->>'state',item->>'office',item->>'district',item->>'incumbency',item->>'fec_status'
   from jsonb_array_elements(payload->'records') item on conflict do nothing;
  insert into public.collection_status(dataset,source_id,latest_snapshot_hash,last_source_check_at,last_database_sync_at,record_count,status)
   values('fec_candidate_filings_2026','fec-candidate-master-2026',digest,source_check,now(),n,'synced')
   on conflict(dataset) do update set latest_snapshot_hash=excluded.latest_snapshot_hash,last_source_check_at=excluded.last_source_check_at,last_database_sync_at=excluded.last_database_sync_at,record_count=excluded.record_count,status=excluded.status;
  update pollingbrain_private.collection_runs set finished_at=now(),success=true where id=run_id;
  return jsonb_build_object('status','synced','records',n,'snapshot_hash',digest);
 exception when others then
  update pollingbrain_private.collection_runs set finished_at=now(),success=false,error_message=sqlerrm where id=run_id;
  return jsonb_build_object('status','failed','run_id',run_id);
 end;
end $fn$;
revoke all on function pollingbrain_private.sync_fec_from_archive() from public,anon,authenticated,service_role;

select cron.schedule('pollingbrain-sync-fec','41 6,18 * * *','select pollingbrain_private.sync_fec_from_archive();');
