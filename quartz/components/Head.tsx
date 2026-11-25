import { i18n } from "../i18n"
import { FullSlug, getFileExtension, joinSegments, pathToRoot } from "../util/path"
import { CSSResourceToStyleElement, JSResourceToScriptElement } from "../util/resources"
import { googleFontHref, googleFontSubsetHref } from "../util/theme"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "./types"
import { unescapeHTML } from "../util/escape"

// 모바일(마우스 올리기가 없는 기기)에서 단어 링크를 누르면 페이지로 넘어가지 않고 뜻만 작은 팝업으로 보여 줌.
// 데스크톱은 그대로(마우스 올리면 Quartz 미리보기, 누르면 이동).
const WORD_POPUP_CSS = `
.wpop{position:fixed;z-index:1000;max-width:min(320px,calc(100vw - 24px));min-width:160px;background:var(--light);color:var(--dark);border:1px solid var(--lightgray);border-radius:10px;box-shadow:0 6px 24px rgba(0,0,0,.35);padding:10px 14px 8px;font-size:.95rem;line-height:1.45}
.wpop-head{display:flex;align-items:center;gap:8px}
.wpop-word{font-weight:700;font-size:1.05rem}
.wpop-snd{border:0;background:var(--highlight);color:inherit;border-radius:6px;padding:2px 7px;font-size:.95rem;cursor:pointer}
.wpop-pos{color:var(--gray);font-size:.8rem;margin-top:1px}
.wpop-mean{margin:6px 0 4px;padding-left:1.2em}
.wpop-mean li{margin:0}
.wpop-more{display:block;text-align:right;font-size:.8rem;color:var(--secondary)!important;text-decoration:none;margin-top:2px}
`

const WORD_POPUP_JS = `(function(){
if(!window.matchMedia('(hover: none)').matches)return;
var cache={},box=null,au=null;
function isWord(a){var s=a.getAttribute('data-slug')||'';return s.indexOf('3-vocabulaire/3-mots/')===0&&!/\\/index$/.test(s)&&(a.getAttribute('href')||'').indexOf('#snd-')<0}
function close(){if(box){box.remove();box=null}if(au){au.pause();au=null}}
function load(url){if(cache[url])return cache[url];
 cache[url]=fetch(url).then(function(r){if(!r.ok&&!/\\.html$/.test(url))return fetch(url+'.html');return r}).then(function(r){if(!r.ok)throw 0;return r.text()}).then(function(t){
  var d=new DOMParser().parseFromString(t,'text/html'),art=d.querySelector('article.popover-hint')||d.body;
  var w=art.querySelector('p strong'),pos=w&&w.parentElement.querySelector('em'),snd=art.querySelector('a[href$=".m4a"]');
  var h=art.querySelector('h2[id="뜻"]'),ol=h&&h.nextElementSibling,m=[];
  if(ol&&/^(OL|UL)$/.test(ol.tagName))[].forEach.call(ol.children,function(li){m.push(li.textContent.trim())});
  return {word:w?w.textContent.trim():'',pos:pos?pos.textContent.trim():'',snd:snd?new URL(snd.getAttribute('href'),url).href:'',mean:m};
 });return cache[url]}
function place(a){var r=a.getBoundingClientRect(),b=box.getBoundingClientRect(),vw=window.innerWidth,vh=window.innerHeight;
 var x=Math.min(Math.max(12,r.left+r.width/2-b.width/2),vw-b.width-12),y=r.bottom+8;
 if(y+b.height>vh-12)y=Math.max(12,r.top-b.height-8);box.style.left=x+'px';box.style.top=y+'px'}
function esc(s){return s.replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function show(a){var url=a.href.split('#')[0];close();
 box=document.createElement('div');box.className='wpop';box.innerHTML='<div class="wpop-word">'+esc(a.textContent.trim())+'</div><div class="wpop-pos">…</div>';
 document.body.appendChild(box);place(a);var me=box;
 load(url).then(function(d){if(box!==me)return;
  box.innerHTML='<div class="wpop-head"><span class="wpop-word">'+esc(d.word||a.textContent.trim())+'</span>'+(d.snd?'<button class="wpop-snd" aria-label="발음 듣기">🔊</button>':'')+'</div>'+(d.pos?'<div class="wpop-pos">'+esc(d.pos)+'</div>':'')+(d.mean.length?'<ol class="wpop-mean">'+d.mean.map(function(x){return'<li>'+esc(x)+'</li>'}).join('')+'</ol>':'')+'<a class="wpop-more" href="'+esc(a.href)+'">자세히 보기 →</a>';
  var b=box.querySelector('.wpop-snd');if(b)b.addEventListener('click',function(e){e.stopPropagation();if(au)au.pause();au=new Audio(d.snd);au.play().catch(function(){})});
  place(a)}).catch(function(){if(box===me)location.href=a.href})}
document.addEventListener('click',function(e){var t=e.target;if(box&&box.contains(t))return;
 var a=t.closest&&t.closest('a');if(a&&isWord(a)){e.preventDefault();e.stopImmediatePropagation();show(a);return}close()},true);
window.addEventListener('scroll',close,{passive:true});document.addEventListener('nav',close);
})();`

export default (() => {
  const Head: QuartzComponent = ({
    cfg,
    fileData,
    externalResources,
    ctx,
  }: QuartzComponentProps) => {
    const titleSuffix = cfg.pageTitleSuffix ?? ""
    const title =
      (fileData.frontmatter?.title ?? i18n(cfg.locale).propertyDefaults.title) + titleSuffix
    const description =
      fileData.frontmatter?.socialDescription ??
      fileData.frontmatter?.description ??
      unescapeHTML(fileData.description?.trim() ?? i18n(cfg.locale).propertyDefaults.description)

    const { css, js, additionalHead } = externalResources

    const url = new URL(`https://${cfg.baseUrl ?? "example.com"}`)
    const path = url.pathname as FullSlug
    const baseDir = fileData.slug === "404" ? path : pathToRoot(fileData.slug!)
    const iconPath = joinSegments(baseDir, "static/icon.png")

    // Url of current page
    const socialUrl =
      fileData.slug === "404" ? url.toString() : joinSegments(url.toString(), fileData.slug!)

    const usesCustomOgImage = ctx.cfg.plugins.emitters.some((e) => e.name === "CustomOgImages")
    const ogImageDefaultPath = `https://${cfg.baseUrl}/static/og-image.png`

    const coreStylesheet = css[0]?.content
    const coreScript = js.find(
      (r) => r.loadTime === "beforeDOMReady" && r.contentType === "external",
    )

    return (
      <head>
        <title>{title}</title>
        <meta charSet="utf-8" />
        {coreStylesheet && <link rel="preload" href={coreStylesheet} as="style" />}
        {coreScript && coreScript.contentType === "external" && (
          <link rel="preload" href={coreScript.src} as="script" />
        )}
        {cfg.theme.cdnCaching && cfg.theme.fontOrigin === "googleFonts" && (
          <>
            <link rel="preconnect" href="https://fonts.googleapis.com" />
            <link rel="preconnect" href="https://fonts.gstatic.com" />
            <link rel="stylesheet" href={googleFontHref(cfg.theme)} />
            {cfg.theme.typography.title && (
              <link rel="stylesheet" href={googleFontSubsetHref(cfg.theme, cfg.pageTitle)} />
            )}
          </>
        )}
        <link rel="preconnect" href="https://cdnjs.cloudflare.com" crossOrigin="anonymous" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />

        <meta name="og:site_name" content={cfg.pageTitle}></meta>
        <meta property="og:title" content={title} />
        <meta property="og:type" content="website" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content={title} />
        <meta name="twitter:description" content={description} />
        <meta property="og:description" content={description} />
        <meta property="og:image:alt" content={description} />

        {!usesCustomOgImage && (
          <>
            <meta property="og:image" content={ogImageDefaultPath} />
            <meta property="og:image:url" content={ogImageDefaultPath} />
            <meta name="twitter:image" content={ogImageDefaultPath} />
            <meta
              property="og:image:type"
              content={`image/${getFileExtension(ogImageDefaultPath) ?? "png"}`}
            />
          </>
        )}

        {cfg.baseUrl && (
          <>
            <meta property="twitter:domain" content={cfg.baseUrl}></meta>
            <meta property="og:url" content={socialUrl}></meta>
            <meta property="twitter:url" content={socialUrl}></meta>
          </>
        )}

        <link rel="icon" href={iconPath} />
        <link rel="apple-touch-icon" sizes="180x180" href={joinSegments(baseDir, "static/apple-touch-icon.png")} />
        <meta name="apple-mobile-web-app-title" content="퀘벡 불어" />
        <meta name="description" content={description} />
        <meta name="generator" content="Quartz" />

        {css.map((resource) => CSSResourceToStyleElement(resource, true))}
        {js
          .filter((resource) => resource.loadTime === "beforeDOMReady")
          .map((res) => JSResourceToScriptElement(res, true))}
        {additionalHead.map((resource) => {
          if (typeof resource === "function") {
            return resource(fileData)
          } else {
            return resource
          }
        })}
        <style dangerouslySetInnerHTML={{ __html: "a[href$='.m4a']{cursor:pointer;text-decoration:none;border-radius:4px;padding:0 2px}a[href$='.m4a']:hover{background:var(--highlight)}a.audio-playing{background:var(--textHighlight)!important}.popover .breadcrumb-container,.popover nav[class*=breadcrumb]{display:none!important}a[href*='#snd-']{color:inherit!important;font-weight:inherit;background:none!important;border-bottom:1px dotted var(--gray);border-radius:0!important;padding:0!important;position:relative;cursor:pointer}a[href*='#snd-']:hover{background:var(--highlight)!important}a.tip-on::after{content:attr(data-tip);position:absolute;left:50%;bottom:calc(100% + 6px);transform:translateX(-50%);white-space:nowrap;background:var(--dark);color:var(--light);font-size:.8rem;font-weight:400;line-height:1.4;padding:3px 8px;border-radius:6px;z-index:50;pointer-events:none}" }} />
        <script dangerouslySetInnerHTML={{ __html: "(function(){var cur=null,curA=null,touch=window.matchMedia('(hover: none)').matches;function stop(){if(cur){cur.pause();cur=null}if(curA){curA.classList.remove('audio-playing');curA=null}}function en1(u){return u.replace('/quebec-francais/en/','/quebec-francais/')}function src(a){var h=a.getAttribute('href')||'';if(/\\.(m4a|mp3|wav|ogg)(\\?|#|$)/i.test(h))return en1(a.href);var i=a.href.indexOf('#snd-');if(i<0)return null;var base=a.href.slice(0,i).split('/3-vocabulaire/')[0];return en1(base+'/_audio/'+a.href.slice(i+5)+'.m4a')}function tipify(a){if(a.title){a.dataset.tip=a.title;a.removeAttribute('title')}}document.addEventListener('click',function(e){var a=e.target.closest&&e.target.closest('a');if(!a)return;var s=src(a);if(!s)return;e.preventDefault();e.stopImmediatePropagation();tipify(a);if(touch&&a.dataset.tip){a.classList.add('tip-on');setTimeout(function(){a.classList.remove('tip-on')},1800)}var same=curA===a;stop();if(same)return;var au=new Audio(s);cur=au;curA=a;a.classList.add('audio-playing');au.addEventListener('ended',stop);au.play().catch(stop)},true);document.addEventListener('mouseover',function(e){var a=e.target.closest&&e.target.closest('a');if(!a)return;var h=a.getAttribute('href')||'';if(/\\.(m4a|mp3|wav|ogg)(\\?|#|$)/i.test(h)){a.setAttribute('data-no-popover','true');a.removeAttribute('title')}else if(h.indexOf('#snd-')>=0){tipify(a)}},true)})();(function(){var MAP={\"🔊\": \"snd\", \"▶\": \"ico i-play\", \"📖\": \"ico i-book\", \"📚\": \"ico i-books\", \"🎙\": \"ico i-mic\", \"🔤\": \"ico i-dict\", \"📂\": \"ico i-folder\", \"💬\": \"ico i-bubble\", \"👉\": \"ico i-arrow\", \"📌\": \"ico i-pin\", \"🗣\": \"ico i-talk\", \"🔢\": \"ico i-num\", \"🎯\": \"ico i-target\", \"📐\": \"ico i-list\", \"📄\": \"ico i-doc\", \"📎\": \"ico i-clip\", \"❌\": \"ico i-xmark\", \"✏\": \"ico i-pencil\", \"📤\": \"ico i-share\", \"📢\": \"ico i-mega\", \"📅\": \"ico i-cal\", \"🎬\": \"ico i-video\", \"🎧\": \"ico i-phones\", \"🍁\": \"ico i-leaf\", \"🌍\": \"ico i-globe\", \"👋\": \"ico i-hand\", \"💍\": \"ico i-heart\", \"➕\": \"ico i-plus\", \"⚠\": \"ico i-warn\", \"🏠\": \"ico i-house\", \"👫\": \"ico i-people\", \"🗓\": \"ico i-cal\", \"📁\": \"ico i-folder\", \"✍\": \"ico i-pencil\", \"✒\": \"ico i-pencil\"},RE=new RegExp('('+Object.keys(MAP).join('|')+')[\\\\uFE0E\\\\uFE0F]?'),SP=new RegExp('('+Object.keys(MAP).join('|')+')[\\\\uFE0E\\\\uFE0F]?');function ic(root){if(!root||!root.nodeType)return;var w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,null),n,todo=[];while(n=w.nextNode()){if(RE.test(n.nodeValue)&&!(n.parentNode&&n.parentNode.closest&&n.parentNode.closest('script,style,textarea,title,.explorer')))todo.push(n)}todo.forEach(function(t){var parts=t.nodeValue.split(SP),f=document.createDocumentFragment();for(var k=0;k<parts.length;k++){var p=parts[k];if(k%2===1){var s=document.createElement('span');s.className=MAP[p];s.setAttribute('aria-hidden','true');f.appendChild(s)}else{if(k>0)p=p.replace(/^ /,'');if(p)f.appendChild(document.createTextNode(p))}}t.parentNode.replaceChild(f,t)})}function go(){ic(document.body)}if(document.readyState!=='loading')go();else document.addEventListener('DOMContentLoaded',go);document.addEventListener('nav',go);new MutationObserver(function(ms){ms.forEach(function(m){m.addedNodes.forEach(function(x){if(x.nodeType===1)ic(x);else if(x.nodeType===3&&RE.test(x.nodeValue)&&x.parentNode)ic(x.parentNode)})})}).observe(document.documentElement,{childList:true,subtree:true})})();(function(){function sw(){var sb=document.querySelector('.sidebar.left');if(!sb||sb.querySelector('.lang-switch'))return;var p=location.pathname,en=/\\/quebec-francais\\/en(\\/|$)/.test(p),to=en?p.replace(/\\/quebec-francais\\/en(\\/|$)/,'/quebec-francais/'):p.replace(/\\/quebec-francais\\/?/,'/quebec-francais/en/');var a=document.createElement('a');a.className='lang-switch';a.href=to+location.hash;a.textContent=en?'한국어':'English';a.setAttribute('data-no-popover','true');var ex=sb.querySelector('.explorer');if(ex)ex.parentNode.insertBefore(a,ex);else sb.appendChild(a)}if(document.readyState!=='loading')sw();else document.addEventListener('DOMContentLoaded',sw);document.addEventListener('nav',sw)})();" }} />
        <style dangerouslySetInnerHTML={{ __html: WORD_POPUP_CSS }} />
        <script dangerouslySetInnerHTML={{ __html: WORD_POPUP_JS }} />
      </head>
    )
  }

  return Head
}) satisfies QuartzComponentConstructor
