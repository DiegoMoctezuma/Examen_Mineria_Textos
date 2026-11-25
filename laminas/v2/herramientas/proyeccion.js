(() => {
  'use strict';
  const slides=[...document.querySelectorAll('.slide')], counter=document.querySelector('#counter');
  const prev=document.querySelector('#prev'),next=document.querySelector('#next');
  let index=0,timer;
  const resize=()=>document.documentElement.style.setProperty('--scale',Math.min(innerWidth/1280,innerHeight/720));
  function show(n,update=true){index=Math.max(0,Math.min(slides.length-1,n));slides.forEach((s,i)=>{s.classList.toggle('active',i===index);s.setAttribute('aria-hidden',String(i!==index));s.inert=i!==index});counter.textContent=`${index+1} / ${slides.length}`;prev.disabled=index===0;next.disabled=index===slides.length-1;document.querySelector('#progress').style.width=`${(index+1)/slides.length*100}%`;if(update)history.replaceState(null,'',`#${index+1}`)}
  const fromHash=()=>{const n=parseInt(location.hash.slice(1),10);show(Number.isFinite(n)?n-1:0,false)};
  function controls(){document.body.classList.add('show-controls');clearTimeout(timer);timer=setTimeout(()=>document.body.classList.remove('show-controls'),2200)}
  async function fullscreen(){try{if(document.fullscreenElement||document.webkitFullscreenElement){const leave=document.exitFullscreen||document.webkitExitFullscreen;await leave.call(document)}else{const enter=document.documentElement.requestFullscreen||document.documentElement.webkitRequestFullscreen;if(!enter)throw Error('Fullscreen unavailable');await enter.call(document.documentElement)}}catch(e){document.querySelector('#hint').textContent='Abre el HTML en Chrome o Edge para usar pantalla completa';controls()}}
  prev.onclick=()=>show(index-1);next.onclick=()=>show(index+1);document.querySelector('#fullscreen').onclick=fullscreen;document.querySelector('#print').onclick=()=>window.print();
  addEventListener('keydown',e=>{if(e.target.closest('input,textarea,select'))return;if(e.key===' '&&e.target.closest('button,a'))return;if(['ArrowRight','ArrowDown',' ','PageDown'].includes(e.key)){e.preventDefault();show(index+1)}else if(['ArrowLeft','ArrowUp','PageUp','Backspace'].includes(e.key)){e.preventDefault();show(index-1)}else if(e.key==='Home'){e.preventDefault();show(0)}else if(e.key==='End'){e.preventDefault();show(slides.length-1)}else if(e.key.toLowerCase()==='f'){e.preventDefault();fullscreen()}else if(e.key==='Escape'){controls()}});
  let touchX=0;addEventListener('touchstart',e=>touchX=e.changedTouches[0].clientX,{passive:true});addEventListener('touchend',e=>{const dx=e.changedTouches[0].clientX-touchX;if(Math.abs(dx)>50)show(index+(dx<0?1:-1));else controls()},{passive:true});
  addEventListener('resize',resize);addEventListener('hashchange',fromHash);addEventListener('mousemove',controls);addEventListener('focusin',controls);
  addEventListener('beforeprint',()=>slides.forEach(s=>s.inert=false));addEventListener('afterprint',()=>show(index,false));
  // Nunca se reduce la tipografía para hacerla caber: la composición se valida al exportar.
  resize();fromHash();controls();document.fonts.ready.then(()=>document.documentElement.dataset.ready='true');
})();
