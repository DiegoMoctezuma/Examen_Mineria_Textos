(() => {
  "use strict";
  const slides=[...document.querySelectorAll('.slide')];
  const counter=document.querySelector('#counter');
  const prev=document.querySelector('#prev'), next=document.querySelector('#next');
  let index=0, timer;
  function resize(){document.documentElement.style.setProperty('--scale',Math.min(innerWidth/1280,innerHeight/720));}
  function show(n,update=true){index=Math.max(0,Math.min(slides.length-1,n));slides.forEach((s,i)=>{s.classList.toggle('active',i===index);s.setAttribute('aria-hidden',String(i!==index));s.inert=i!==index});counter.textContent=`${index+1} / ${slides.length}`;prev.disabled=index===0;next.disabled=index===slides.length-1;document.querySelector('#progress').style.width=`${(index+1)/slides.length*100}%`;if(update)history.replaceState(null,'',`#${index+1}`);}
  function fromHash(){const n=parseInt(location.hash.slice(1),10);show(Number.isFinite(n)?n-1:0,false);}
  function controls(){document.body.classList.add('show-controls');clearTimeout(timer);timer=setTimeout(()=>document.body.classList.remove('show-controls'),2400);}
  async function fullscreen(){try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen();}catch(e){controls();}}
  prev.onclick=()=>show(index-1);next.onclick=()=>show(index+1);document.querySelector('#fullscreen').onclick=fullscreen;document.querySelector('#print').onclick=()=>window.print();
  addEventListener('keydown',e=>{if(e.target.closest('input,textarea,select'))return;if(e.key===' '&&e.target.closest('button,a'))return;if(['ArrowRight','ArrowDown',' ','PageDown'].includes(e.key)){e.preventDefault();show(index+1)}else if(['ArrowLeft','ArrowUp','PageUp','Backspace'].includes(e.key)){e.preventDefault();show(index-1)}else if(e.key==='Home'){e.preventDefault();show(0)}else if(e.key==='End'){e.preventDefault();show(slides.length-1)}else if(e.key.toLowerCase()==='f'){e.preventDefault();fullscreen()}else if(e.key==='Escape'){controls()}});
  let touchX=0;addEventListener('touchstart',e=>{touchX=e.changedTouches[0].clientX},{passive:true});addEventListener('touchend',e=>{const dx=e.changedTouches[0].clientX-touchX;if(Math.abs(dx)>50)show(index+(dx<0?1:-1));else controls()},{passive:true});
  addEventListener('hashchange',fromHash);addEventListener('resize',resize);addEventListener('mousemove',controls);addEventListener('focusin',controls);
  // El texto aprobado conserva su tamaño salvo ajuste mínimo por métricas tipográficas del navegador.
  async function fit(){await document.fonts.ready;document.querySelectorAll('.text').forEach(el=>{let tries=0;while((el.scrollHeight>el.clientHeight+1||el.scrollWidth>el.clientWidth+1)&&tries++<9){el.querySelectorAll('span,a').forEach(s=>s.style.fontSize=(parseFloat(s.style.fontSize)*.985)+'px')}});document.documentElement.dataset.ready='true';}
  addEventListener('beforeprint',()=>slides.forEach(s=>s.inert=false));addEventListener('afterprint',()=>show(index,false));
  resize();fromHash();controls();fit();
})();
