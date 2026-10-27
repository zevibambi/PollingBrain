'use strict';
(async () => {
 const base = 'https://rrqxrbutruvofvhveukl.supabase.co/rest/v1/';
 const key = 'sb_publishable_tb_kJRHZiDVdGGkeGOcnbA_6ecje2PJ';
 const sourceListing = document.getElementById('sources');
 const status = document.getElementById('databaseStatus');
 const listing = document.getElementById('verifiedPolls');
 async function query(table, parameters) {
  const response = await fetch(base + table + '?' + parameters, {headers:{apikey:key}, signal:AbortSignal.timeout(15000)});
  if (!response.ok) throw new Error('Database request failed');
  return response.json();
 }
 const outcomes = await Promise.allSettled([
  query('collection_status','select=dataset,record_count,last_source_check_at,last_database_sync_at,status,latest_snapshot_hash'),
  query('polls','select=race_id,pollster,field_start,field_end,sample_size,population,results,original_release_url,review_notes&review_status=eq.verified&order=field_end.desc&limit=200')
 ]);
 if(outcomes[0].status === 'fulfilled') {
  const fec = outcomes[0].value.find(row => row.dataset === 'fec_candidate_filings_2026');
  status.textContent = fec ? 'Database connected. '+fec.record_count.toLocaleString()+' FEC filing records in the latest snapshot. Source checked '+new Date(fec.last_source_check_at).toLocaleString()+'. Database synced '+new Date(fec.last_database_sync_at).toLocaleString()+'.' : 'Database connected. First collection pending.';
  if(fec) {
   document.getElementById('filed').textContent=fec.record_count.toLocaleString();
   await Promise.allSettled([['H','house'],['S','senate']].map(async ([office,id])=>{
    const response=await fetch(base+'candidate_filings?select=fec_id&snapshot_hash=eq.'+encodeURIComponent(fec.latest_snapshot_hash)+'&office=eq.'+office,{method:'HEAD',headers:{apikey:key,Prefer:'count=exact'},signal:AbortSignal.timeout(15000)});
    if(!response.ok) return;
    const total=Number((response.headers.get('content-range')||'').split('/')[1]);
    if(Number.isFinite(total)) document.getElementById(id).textContent=total.toLocaleString();
   }));
  }
 } else { status.textContent = 'Database connection unavailable. Static source downloads remain available below.'; }
 if(outcomes[1].status === 'fulfilled') {
  const polls = outcomes[1].value;
  document.getElementById('verifiedPollCount').textContent = polls.length === 200 ? '200+' : String(polls.length);
  listing.textContent = '';
  if(!polls.length) listing.textContent = 'No verified poll observations published yet.';
  for(const poll of polls) {
   const article = document.createElement('article');
   const heading = document.createElement('h3');
   heading.textContent = poll.race_id+' · '+poll.pollster;
   article.appendChild(heading);
   const metadata = document.createElement('p');
   metadata.textContent = 'Fieldwork '+poll.field_start+' to '+poll.field_end+' · '+(poll.sample_size || 'Unknown sample size')+' '+poll.population;
   article.appendChild(metadata);
   const result = document.createElement('p');
   result.textContent = poll.results.map(item=>item.name+' '+item.percentage+'%').join(' · ');
   article.appendChild(result);
   const note = document.createElement('p');
   note.textContent = poll.review_notes;
   article.appendChild(note);
   const link = document.createElement('a');
   const url = new URL(poll.original_release_url);
   if(url.protocol === 'https:') { link.href=url.href;link.textContent='Read original poll release';link.target='_blank';link.rel='noopener noreferrer';article.appendChild(link); }
   listing.appendChild(article);
  }
 } else { listing.textContent='Poll database unavailable. No placeholder polls are shown.'; }

 try {
  const sources=await query('data_sources','select=publisher,category,source_url,status,caution&order=id.asc');
  sourceListing.textContent='';
  for(const source of sources) {
   const article=document.createElement('article');
   const heading=document.createElement('h3');heading.textContent=source.publisher;article.appendChild(heading);
   const state=document.createElement('span');state.className='status';state.textContent=source.status.replaceAll('_',' ');article.appendChild(state);
   const note=document.createElement('p');note.textContent=source.caution;article.appendChild(note);
   if(source.source_url && new URL(source.source_url).protocol==='https:') {const a=document.createElement('a');a.href=source.source_url;a.textContent='View original source';a.rel='noopener noreferrer';a.target='_blank';article.appendChild(a);}
   sourceListing.appendChild(article);
  }
 } catch (_) {sourceListing.textContent='Live source registry unavailable. Download the source registry below.';}
})();