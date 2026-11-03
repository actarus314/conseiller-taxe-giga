const {JSDOM}=require('jsdom');const fs=require('fs');
const path=require('path'),ROOT=path.join(__dirname,'..','..');
// node test.js        → teste conseiller.js ; node test.js bm → teste le favori généré
const SRC=process.argv[2]==='bm'?decodeURIComponent(fs.readFileSync(path.join(ROOT,'bookmarklet.txt'),'utf8').trim().slice(11)):fs.readFileSync(path.join(ROOT,'conseiller.js'),'utf8');
const int=n=>new Intl.NumberFormat('fr-FR').format(n),nf=d=>new Intl.NumberFormat('fr-FR',{minimumFractionDigits:d,maximumFractionDigits:d});
const big=n=>n<1e6?int(Math.floor(n)):n<1e9?nf(2).format(n/1e6)+' M':nf(2).format(n/1e9)+' Md';
const B={doigt:10,stagiaire:15,chat:100,hamster:600,souris:500,bot:6000,fax:6e4,commission:6e5,gant:15e4,satellite:5e6,trounoir:7.5e7,tampon:2e7,datacenter:1e9};
function test(label,owned,wallet,{mode='passif',cps=5,perClick,chip,fakePrice}={}){
  const items=Object.entries(owned).map(([id,n])=>{const c=fakePrice&&fakePrice[id]||Math.ceil(B[id]*1.15**n);return `<button class="item" data-id="${id}" ${wallet<c?'disabled':''}><span class="ic"><b class="own">×${n}</b><small class="price">💰 ${big(c)}</small></span></button>`}).join('');
  const dom=new JSDOM(`<title>Jeu</title><b id="wallet">${big(wallet)}</b><span id="perClick">${perClick||''}</span><p id="buffChip" ${chip?'':'hidden'}>${chip||''}</p><button id="stickyTax" style="height:70px">T</button><div id="shop">${items}</div>`,{runScripts:'outside-only',url:'https://taxe-au-giga.fr/'});
  const w=dom.window,d=w.document; w.localStorage.setItem('tagAdv-mode',mode); w.localStorage.setItem('tagAdv-cps',String(cps));
  w.eval(SRC);
  console.log('==',label);console.log(' ',d.querySelector('#tagAdv .now').textContent);
  console.log([...d.querySelectorAll('#tagAdv li')].map(l=>'   '+l.textContent).join('\n'));
  console.log(' ',d.querySelector('#tagAdv .ft').textContent,'| warn:',d.querySelector('#tagAdv .warn').hidden?'-':d.querySelector('#tagAdv .warn').textContent);
  console.log('  badge:',d.querySelector('.tagAdvBest')?.dataset.id,d.querySelector('.tagAdvBest')?.dataset.adv,'| bottom:',d.querySelector('#tagAdv').style.bottom);
  w.eval('window.__tagAdv.stop()');if(d.querySelector('#tagAdv'))console.log('  ARRÊT KO');w.close();
}
const o={doigt:14,stagiaire:32,chat:29,hamster:25,souris:6,bot:20,fax:15,commission:11,gant:9,satellite:2,trounoir:0,tampon:0};
test('passif 11h52',o,9847633,{perClick:'5 770 visites'});
test('actif 5/s 11h52',o,9847633,{mode:'actif',perClick:'5 770 visites'});
test('actif 3/s',o,9847633,{mode:'actif',cps:3,perClick:'5 770 visites'});
test('passif + frénésie 40 s',{...o,hamster:26,bot:21,fax:16,satellite:3},2628957,{perClick:'5 803 visites',chip:'🔥 Frénésie fiscale : production ×3 encore 40 s'});
test('puissance de clic fausse',o,9847633,{perClick:'9 999 visites'});
