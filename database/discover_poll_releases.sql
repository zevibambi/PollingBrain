
create table public.source_discoveries (
 id uuid primary key default gen_random_uuid(),
 source_id text not null references public.data_sources(id),
 source_url text not null, headline text not null, published_at timestamptz not null,
 first_seen_at timestamptz not null default now(), last_seen_at timestamptz not null default now(),
 review_status text not null default 'pending' check(review_status in ('pending','verified','rejected')),
 unique(source_id,source_url)
);
create index on public.source_discoveries(review_status,published_at desc);
alter table public.source_discoveries enable row level security;
revoke all on public.source_discoveries from anon,authenticated;
grant select on public.source_discoveries to anon,authenticated;
grant select,insert,update,delete on public.source_discoveries to service_role;
create policy verified_discoveries on public.source_discoveries for select to anon,authenticated using(review_status='verified');
insert into public.data_sources(id,publisher,category,source_url,status,caution) values
 ('siena-release-feed','Siena Research Institute','poll_release_feed','https://sri.siena.edu/feed/','collection_enabled','Discovery metadata only. New releases require poll extraction and source checking.'),
 ('marquette-release-feed','Marquette Law School Poll','poll_release_feed','https://law.marquette.edu/poll/feed/','collection_enabled','Discovery metadata only. New releases require poll extraction and source checking.');
create function pollingbrain_private.discover_poll_releases() returns jsonb
language plpgsql security invoker set search_path='' as $fn$
declare source record; response extensions.http_response; feed xml; items xml[]; item xml;
 item_url text; title text; published timestamptz; n integer; run_id bigint; outcomes jsonb:='[]';
begin
 if not pg_try_advisory_xact_lock(260028) then return jsonb_build_object('status','already_running'); end if;
 for source in select * from (values
  ('siena-release-feed','https://sri.siena.edu/feed/','https://sri.siena.edu/'),
  ('marquette-release-feed','https://law.marquette.edu/poll/feed/','https://law.marquette.edu/')
 ) as feeds(id,url,allowed_prefix) loop
  insert into pollingbrain_private.collection_runs(dataset) values(source.id) returning id into run_id;
  begin
   perform extensions.http_set_curlopt('CURLOPT_TIMEOUT_MS','20000');
   select * into response from extensions.http_get(source.url);
   if response.status <> 200 or octet_length(response.content)>2000000 then raise exception 'Feed HTTP or size check failed'; end if;
   feed:=response.content::xml;items:=xpath('/rss/channel/item',feed);n:=coalesce(array_length(items,1),0);
   if n=0 or n>100 then raise exception 'Unexpected feed item count'; end if;
   foreach item in array items loop
    item_url:=(xpath('string(/item/link)',item))[1]::text;
    title:=(xpath('string(/item/title)',item))[1]::text;
    published:=((xpath('string(/item/pubDate)',item))[1]::text)::timestamptz;
    if left(item_url,length(source.allowed_prefix))<>source.allowed_prefix or title is null or length(title)=0 or published is null then raise exception 'Feed metadata invalid'; end if;
    insert into public.source_discoveries(source_id,source_url,headline,published_at)
     values(source.id,item_url,title,published)
     on conflict(source_id,source_url) do update set last_seen_at=now();
   end loop;
   insert into public.collection_status(dataset,source_id,last_source_check_at,last_database_sync_at,record_count,status)
    values(source.id,source.id,now(),now(),n,'discovery_only')
    on conflict(dataset) do update set last_source_check_at=now(),last_database_sync_at=now(),record_count=excluded.record_count,status=excluded.status;
   update pollingbrain_private.collection_runs set finished_at=now(),success=true where id=run_id;
   outcomes:=outcomes||jsonb_build_array(jsonb_build_object('source',source.id,'discovered',n));
  exception when others then
   update pollingbrain_private.collection_runs set finished_at=now(),success=false,error_message=sqlerrm where id=run_id;
   outcomes:=outcomes||jsonb_build_array(jsonb_build_object('source',source.id,'status','failed','run_id',run_id));
  end;
 end loop;
 return outcomes;
end $fn$;
revoke all on function pollingbrain_private.discover_poll_releases() from public,anon,authenticated,service_role;
select cron.schedule('pollingbrain-discover-polls','17 */2 * * *','select pollingbrain_private.discover_poll_releases();');
