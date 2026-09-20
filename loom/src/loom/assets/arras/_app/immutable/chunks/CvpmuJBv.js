var e=window,t=e.ShadowRoot&&(e.ShadyCSS===void 0||e.ShadyCSS.nativeShadow)&&`adoptedStyleSheets`in Document.prototype&&`replace`in CSSStyleSheet.prototype,n=Symbol(),r=new WeakMap,i=class{constructor(e,t,r){if(this._$cssResult$=!0,r!==n)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=t}get styleSheet(){let e=this.o,n=this.t;if(t&&e===void 0){let t=n!==void 0&&n.length===1;t&&(e=r.get(n)),e===void 0&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),t&&r.set(n,e))}return e}toString(){return this.cssText}},a=e=>new i(typeof e==`string`?e:e+``,void 0,n),o=(e,...t)=>new i(e.length===1?e[0]:t.reduce(((t,n,r)=>t+(e=>{if(!0===e._$cssResult$)return e.cssText;if(typeof e==`number`)return e;throw Error(`Value passed to 'css' function must be a 'css' function result: `+e+`. Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.`)})(n)+e[r+1]),e[0]),e,n),s=(n,r)=>{t?n.adoptedStyleSheets=r.map((e=>e instanceof CSSStyleSheet?e:e.styleSheet)):r.forEach((t=>{let r=document.createElement(`style`),i=e.litNonce;i!==void 0&&r.setAttribute(`nonce`,i),r.textContent=t.cssText,n.appendChild(r)}))},c=t?e=>e:e=>e instanceof CSSStyleSheet?(e=>{let t=``;for(let n of e.cssRules)t+=n.cssText;return a(t)})(e):e,l=window,u=l.trustedTypes,d=u?u.emptyScript:``,f=l.reactiveElementPolyfillSupport,p={toAttribute(e,t){switch(t){case Boolean:e=e?d:null;break;case Object:case Array:e=e==null?e:JSON.stringify(e)}return e},fromAttribute(e,t){let n=e;switch(t){case Boolean:n=e!==null;break;case Number:n=e===null?null:Number(e);break;case Object:case Array:try{n=JSON.parse(e)}catch{n=null}}return n}},m=(e,t)=>t!==e&&(t==t||e==e),ee={attribute:!0,type:String,converter:p,reflect:!1,hasChanged:m},te=`finalized`,h=class extends HTMLElement{constructor(){super(),this._$Ei=new Map,this.isUpdatePending=!1,this.hasUpdated=!1,this._$El=null,this._$Eu()}static addInitializer(e){this.finalize(),(this.h??=[]).push(e)}static get observedAttributes(){this.finalize();let e=[];return this.elementProperties.forEach(((t,n)=>{let r=this._$Ep(n,t);r!==void 0&&(this._$Ev.set(r,n),e.push(r))})),e}static createProperty(e,t=ee){if(t.state&&(t.attribute=!1),this.finalize(),this.elementProperties.set(e,t),!t.noAccessor&&!this.prototype.hasOwnProperty(e)){let n=typeof e==`symbol`?Symbol():`__`+e,r=this.getPropertyDescriptor(e,n,t);r!==void 0&&Object.defineProperty(this.prototype,e,r)}}static getPropertyDescriptor(e,t,n){return{get(){return this[t]},set(r){let i=this[e];this[t]=r,this.requestUpdate(e,i,n)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){return this.elementProperties.get(e)||ee}static finalize(){if(this.hasOwnProperty(te))return!1;this[te]=!0;let e=Object.getPrototypeOf(this);if(e.finalize(),e.h!==void 0&&(this.h=[...e.h]),this.elementProperties=new Map(e.elementProperties),this._$Ev=new Map,this.hasOwnProperty(`properties`)){let e=this.properties,t=[...Object.getOwnPropertyNames(e),...Object.getOwnPropertySymbols(e)];for(let n of t)this.createProperty(n,e[n])}return this.elementStyles=this.finalizeStyles(this.styles),!0}static finalizeStyles(e){let t=[];if(Array.isArray(e)){let n=new Set(e.flat(1/0).reverse());for(let e of n)t.unshift(c(e))}else e!==void 0&&t.push(c(e));return t}static _$Ep(e,t){let n=t.attribute;return!1===n?void 0:typeof n==`string`?n:typeof e==`string`?e.toLowerCase():void 0}_$Eu(){var e;this._$E_=new Promise((e=>this.enableUpdating=e)),this._$AL=new Map,this._$Eg(),this.requestUpdate(),(e=this.constructor.h)==null||e.forEach((e=>e(this)))}addController(e){var t;(this._$ES??=[]).push(e),this.renderRoot!==void 0&&this.isConnected&&((t=e.hostConnected)==null||t.call(e))}removeController(e){var t;(t=this._$ES)==null||t.splice(this._$ES.indexOf(e)>>>0,1)}_$Eg(){this.constructor.elementProperties.forEach(((e,t)=>{this.hasOwnProperty(t)&&(this._$Ei.set(t,this[t]),delete this[t])}))}createRenderRoot(){let e=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return s(e,this.constructor.elementStyles),e}connectedCallback(){var e;this.renderRoot===void 0&&(this.renderRoot=this.createRenderRoot()),this.enableUpdating(!0),(e=this._$ES)==null||e.forEach((e=>e.hostConnected?.call(e)))}enableUpdating(e){}disconnectedCallback(){var e;(e=this._$ES)==null||e.forEach((e=>e.hostDisconnected?.call(e)))}attributeChangedCallback(e,t,n){this._$AK(e,n)}_$EO(e,t,n=ee){let r=this.constructor._$Ep(e,n);if(r!==void 0&&!0===n.reflect){let i=(n.converter?.toAttribute===void 0?p:n.converter).toAttribute(t,n.type);this._$El=e,i==null?this.removeAttribute(r):this.setAttribute(r,i),this._$El=null}}_$AK(e,t){let n=this.constructor,r=n._$Ev.get(e);if(r!==void 0&&this._$El!==r){let e=n.getPropertyOptions(r),i=typeof e.converter==`function`?{fromAttribute:e.converter}:e.converter?.fromAttribute===void 0?p:e.converter;this._$El=r,this[r]=i.fromAttribute(t,e.type),this._$El=null}}requestUpdate(e,t,n){let r=!0;e!==void 0&&(((n||=this.constructor.getPropertyOptions(e)).hasChanged||m)(this[e],t)?(this._$AL.has(e)||this._$AL.set(e,t),!0===n.reflect&&this._$El!==e&&(this._$EC===void 0&&(this._$EC=new Map),this._$EC.set(e,n))):r=!1),!this.isUpdatePending&&r&&(this._$E_=this._$Ej())}async _$Ej(){this.isUpdatePending=!0;try{await this._$E_}catch(e){Promise.reject(e)}let e=this.scheduleUpdate();return e!=null&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){var e;if(!this.isUpdatePending)return;this.hasUpdated,this._$Ei&&=(this._$Ei.forEach(((e,t)=>this[t]=e)),void 0);let t=!1,n=this._$AL;try{t=this.shouldUpdate(n),t?(this.willUpdate(n),(e=this._$ES)==null||e.forEach((e=>e.hostUpdate?.call(e))),this.update(n)):this._$Ek()}catch(e){throw t=!1,this._$Ek(),e}t&&this._$AE(n)}willUpdate(e){}_$AE(e){var t;(t=this._$ES)==null||t.forEach((e=>e.hostUpdated?.call(e))),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$Ek(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$E_}shouldUpdate(e){return!0}update(e){this._$EC!==void 0&&(this._$EC.forEach(((e,t)=>this._$EO(t,this[t],e))),this._$EC=void 0),this._$Ek()}updated(e){}firstUpdated(e){}};h[te]=!0,h.elementProperties=new Map,h.elementStyles=[],h.shadowRootOptions={mode:`open`},f?.({ReactiveElement:h}),(l.reactiveElementVersions??=[]).push(`1.6.3`);var ne=window,g=ne.trustedTypes,re=g?g.createPolicy(`lit-html`,{createHTML:e=>e}):void 0,_=`$lit$`,v=`lit$${(Math.random()+``).slice(9)}$`,ie=`?`+v,ae=`<${ie}>`,y=document,b=()=>y.createComment(``),x=e=>e===null||typeof e!=`object`&&typeof e!=`function`,oe=Array.isArray,se=e=>oe(e)||typeof e?.[Symbol.iterator]==`function`,ce=`[ 	
\f\r]`,S=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,le=/-->/g,ue=/>/g,C=RegExp(`>|${ce}(?:([^\\s"'>=/]+)(${ce}*=${ce}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,`g`),de=/'/g,fe=/"/g,pe=/^(?:script|style|textarea|title)$/i,w=(e=>(t,...n)=>({_$litType$:e,strings:t,values:n}))(1),T=Symbol.for(`lit-noChange`),E=Symbol.for(`lit-nothing`),me=new WeakMap,D=y.createTreeWalker(y,129,null,!1);function he(e,t){if(!Array.isArray(e)||!e.hasOwnProperty(`raw`))throw Error(`invalid template strings array`);return re===void 0?t:re.createHTML(t)}var ge=(e,t)=>{let n=e.length-1,r=[],i,a=t===2?`<svg>`:``,o=S;for(let t=0;t<n;t++){let n=e[t],s,c,l=-1,u=0;for(;u<n.length&&(o.lastIndex=u,c=o.exec(n),c!==null);)u=o.lastIndex,o===S?c[1]===`!--`?o=le:c[1]===void 0?c[2]===void 0?c[3]!==void 0&&(o=C):(pe.test(c[2])&&(i=RegExp(`</`+c[2],`g`)),o=C):o=ue:o===C?c[0]===`>`?(o=i??S,l=-1):c[1]===void 0?l=-2:(l=o.lastIndex-c[2].length,s=c[1],o=c[3]===void 0?C:c[3]===`"`?fe:de):o===fe||o===de?o=C:o===le||o===ue?o=S:(o=C,i=void 0);let d=o===C&&e[t+1].startsWith(`/>`)?` `:``;a+=o===S?n+ae:l>=0?(r.push(s),n.slice(0,l)+_+n.slice(l)+v+d):n+v+(l===-2?(r.push(void 0),t):d)}return[he(e,a+(e[n]||`<?>`)+(t===2?`</svg>`:``)),r]},_e=class e{constructor({strings:t,_$litType$:n},r){let i;this.parts=[];let a=0,o=0,s=t.length-1,c=this.parts,[l,u]=ge(t,n);if(this.el=e.createElement(l,r),D.currentNode=this.el.content,n===2){let e=this.el.content,t=e.firstChild;t.remove(),e.append(...t.childNodes)}for(;(i=D.nextNode())!==null&&c.length<s;){if(i.nodeType===1){if(i.hasAttributes()){let e=[];for(let t of i.getAttributeNames())if(t.endsWith(_)||t.startsWith(v)){let n=u[o++];if(e.push(t),n!==void 0){let e=i.getAttribute(n.toLowerCase()+_).split(v),t=/([.?@])?(.*)/.exec(n);c.push({type:1,index:a,name:t[2],strings:e,ctor:t[1]===`.`?ye:t[1]===`?`?xe:t[1]===`@`?Se:A})}else c.push({type:6,index:a})}for(let t of e)i.removeAttribute(t)}if(pe.test(i.tagName)){let e=i.textContent.split(v),t=e.length-1;if(t>0){i.textContent=g?g.emptyScript:``;for(let n=0;n<t;n++)i.append(e[n],b()),D.nextNode(),c.push({type:2,index:++a});i.append(e[t],b())}}}else if(i.nodeType===8){if(i.data===ie)c.push({type:2,index:a});else{let e=-1;for(;(e=i.data.indexOf(v,e+1))!==-1;)c.push({type:7,index:a}),e+=v.length-1}}a++}}static createElement(e,t){let n=y.createElement(`template`);return n.innerHTML=e,n}};function O(e,t,n=e,r){var i,a;if(t===T)return t;let o=r===void 0?n._$Cl:n._$Co?.[r],s=x(t)?void 0:t._$litDirective$;return o?.constructor!==s&&((i=o?._$AO)==null||i.call(o,!1),s===void 0?o=void 0:(o=new s(e),o._$AT(e,n,r)),r===void 0?n._$Cl=o:((a=n)._$Co??(a._$Co=[]))[r]=o),o!==void 0&&(t=O(e,o._$AS(e,t.values),o,r)),t}var ve=class{constructor(e,t){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=t}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){let{el:{content:t},parts:n}=this._$AD,r=(e?.creationScope??y).importNode(t,!0);D.currentNode=r;let i=D.nextNode(),a=0,o=0,s=n[0];for(;s!==void 0;){if(a===s.index){let t;s.type===2?t=new k(i,i.nextSibling,this,e):s.type===1?t=new s.ctor(i,s.name,s.strings,this,e):s.type===6&&(t=new Ce(i,this,e)),this._$AV.push(t),s=n[++o]}a!==s?.index&&(i=D.nextNode(),a++)}return D.currentNode=y,r}v(e){let t=0;for(let n of this._$AV)n!==void 0&&(n.strings===void 0?n._$AI(e[t]):(n._$AI(e,n,t),t+=n.strings.length-2)),t++}},k=class e{constructor(e,t,n,r){var i;this.type=2,this._$AH=E,this._$AN=void 0,this._$AA=e,this._$AB=t,this._$AM=n,this.options=r,this._$Cp=(i=r?.isConnected)==null||i}get _$AU(){return this._$AM?._$AU??this._$Cp}get parentNode(){let e=this._$AA.parentNode,t=this._$AM;return t!==void 0&&e?.nodeType===11&&(e=t.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,t=this){e=O(this,e,t),x(e)?e===E||e==null||e===``?(this._$AH!==E&&this._$AR(),this._$AH=E):e!==this._$AH&&e!==T&&this._(e):e._$litType$===void 0?e.nodeType===void 0?se(e)?this.T(e):this._(e):this.$(e):this.g(e)}k(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}$(e){this._$AH!==e&&(this._$AR(),this._$AH=this.k(e))}_(e){this._$AH!==E&&x(this._$AH)?this._$AA.nextSibling.data=e:this.$(y.createTextNode(e)),this._$AH=e}g(e){let{values:t,_$litType$:n}=e,r=typeof n==`number`?this._$AC(e):(n.el===void 0&&(n.el=_e.createElement(he(n.h,n.h[0]),this.options)),n);if(this._$AH?._$AD===r)this._$AH.v(t);else{let e=new ve(r,this),n=e.u(this.options);e.v(t),this.$(n),this._$AH=e}}_$AC(e){let t=me.get(e.strings);return t===void 0&&me.set(e.strings,t=new _e(e)),t}T(t){oe(this._$AH)||(this._$AH=[],this._$AR());let n=this._$AH,r,i=0;for(let a of t)i===n.length?n.push(r=new e(this.k(b()),this.k(b()),this,this.options)):r=n[i],r._$AI(a),i++;i<n.length&&(this._$AR(r&&r._$AB.nextSibling,i),n.length=i)}_$AR(e=this._$AA.nextSibling,t){var n;for((n=this._$AP)==null||n.call(this,!1,!0,t);e&&e!==this._$AB;){let t=e.nextSibling;e.remove(),e=t}}setConnected(e){var t;this._$AM===void 0&&(this._$Cp=e,(t=this._$AP)==null||t.call(this,e))}},A=class{constructor(e,t,n,r,i){this.type=1,this._$AH=E,this._$AN=void 0,this.element=e,this.name=t,this._$AM=r,this.options=i,n.length>2||n[0]!==``||n[1]!==``?(this._$AH=Array(n.length-1).fill(new String),this.strings=n):this._$AH=E}get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}_$AI(e,t=this,n,r){let i=this.strings,a=!1;if(i===void 0)e=O(this,e,t,0),a=!x(e)||e!==this._$AH&&e!==T,a&&(this._$AH=e);else{let r=e,o,s;for(e=i[0],o=0;o<i.length-1;o++)s=O(this,r[n+o],t,o),s===T&&(s=this._$AH[o]),a||=!x(s)||s!==this._$AH[o],s===E?e=E:e!==E&&(e+=(s??``)+i[o+1]),this._$AH[o]=s}a&&!r&&this.j(e)}j(e){e===E?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e??``)}},ye=class extends A{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===E?void 0:e}},be=g?g.emptyScript:``,xe=class extends A{constructor(){super(...arguments),this.type=4}j(e){e&&e!==E?this.element.setAttribute(this.name,be):this.element.removeAttribute(this.name)}},Se=class extends A{constructor(e,t,n,r,i){super(e,t,n,r,i),this.type=5}_$AI(e,t=this){if((e=O(this,e,t,0)??E)===T)return;let n=this._$AH,r=e===E&&n!==E||e.capture!==n.capture||e.once!==n.once||e.passive!==n.passive,i=e!==E&&(n===E||r);r&&this.element.removeEventListener(this.name,this,n),i&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){typeof this._$AH==`function`?this._$AH.call(this.options?.host??this.element,e):this._$AH.handleEvent(e)}},Ce=class{constructor(e,t,n){this.element=e,this.type=6,this._$AN=void 0,this._$AM=t,this.options=n}get _$AU(){return this._$AM._$AU}_$AI(e){O(this,e)}},we={O:_,P:v,A:ie,C:1,M:ge,L:ve,R:se,D:O,I:k,V:A,H:xe,N:Se,U:ye,F:Ce},Te=ne.litHtmlPolyfillSupport;Te?.(_e,k),(ne.litHtmlVersions??=[]).push(`2.8.0`);var Ee=(e,t,n)=>{let r=n?.renderBefore??t,i=r._$litPart$;if(i===void 0){let e=n?.renderBefore??null;r._$litPart$=i=new k(t.insertBefore(b(),e),e,void 0,n??{})}return i._$AI(e),i},De,j=class extends h{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){var e;let t=super.createRenderRoot();return(e=this.renderOptions).renderBefore??(e.renderBefore=t.firstChild),t}update(e){let t=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=Ee(t,this.renderRoot,this.renderOptions)}connectedCallback(){var e;super.connectedCallback(),(e=this._$Do)==null||e.setConnected(!0)}disconnectedCallback(){var e;super.disconnectedCallback(),(e=this._$Do)==null||e.setConnected(!1)}render(){return T}};j.finalized=!0,j._$litElement$=!0,(De=globalThis.litElementHydrateSupport)==null||De.call(globalThis,{LitElement:j});var Oe=globalThis.litElementPolyfillSupport;Oe?.({LitElement:j}),(globalThis.litElementVersions??(globalThis.litElementVersions=[])).push(`3.3.3`);var M=e=>t=>typeof t==`function`?((e,t)=>(customElements.define(e,t),t))(e,t):((e,t)=>{let{kind:n,elements:r}=t;return{kind:n,elements:r,finisher(t){customElements.define(e,t)}}})(e,t),ke=(e,t)=>t.kind===`method`&&t.descriptor&&!(`value`in t.descriptor)?{...t,finisher(n){n.createProperty(t.key,e)}}:{kind:`field`,key:Symbol(),placement:`own`,descriptor:{},originalKey:t.key,initializer(){typeof t.initializer==`function`&&(this[t.key]=t.initializer.call(this))},finisher(n){n.createProperty(t.key,e)}},Ae=(e,t,n)=>{t.constructor.createProperty(n,e)};function N(e){return(t,n)=>n===void 0?ke(e,t):Ae(e,t,n)}function P(e){return N({...e,state:!0})}window.HTMLSlotElement?.prototype.assignedElements;var F={ATTRIBUTE:1,CHILD:2,PROPERTY:3,BOOLEAN_ATTRIBUTE:4,EVENT:5,ELEMENT:6},I=e=>(...t)=>({_$litDirective$:e,values:t}),L=class{constructor(e){}get _$AU(){return this._$AM._$AU}_$AT(e,t,n){this._$Ct=e,this._$AM=t,this._$Ci=n}_$AS(e,t){return this.update(e,t)}update(e,t){return this.render(...t)}},{I:je}=we,Me=e=>e.strings===void 0,Ne=()=>document.createComment(``),R=(e,t,n)=>{var r;let i=e._$AA.parentNode,a=t===void 0?e._$AB:t._$AA;if(n===void 0)n=new je(i.insertBefore(Ne(),a),i.insertBefore(Ne(),a),e,e.options);else{let t=n._$AB.nextSibling,o=n._$AM,s=o!==e;if(s){let t;(r=n._$AQ)==null||r.call(n,e),n._$AM=e,n._$AP!==void 0&&(t=e._$AU)!==o._$AU&&n._$AP(t)}if(t!==a||s){let e=n._$AA;for(;e!==t;){let t=e.nextSibling;i.insertBefore(e,a),e=t}}}return n},z=(e,t,n=e)=>(e._$AI(t,n),e),Pe={},Fe=(e,t=Pe)=>e._$AH=t,Ie=e=>e._$AH,Le=e=>{var t;(t=e._$AP)==null||t.call(e,!1,!0);let n=e._$AA,r=e._$AB.nextSibling;for(;n!==r;){let e=n.nextSibling;n.remove(),n=e}},Re=(e,t,n)=>{let r=new Map;for(let i=t;i<=n;i++)r.set(e[i],i);return r},ze=I(class extends L{constructor(e){if(super(e),e.type!==F.CHILD)throw Error(`repeat() can only be used in text expressions`)}ct(e,t,n){let r;n===void 0?n=t:t!==void 0&&(r=t);let i=[],a=[],o=0;for(let t of e)i[o]=r?r(t,o):o,a[o]=n(t,o),o++;return{values:a,keys:i}}render(e,t,n){return this.ct(e,t,n).values}update(e,[t,n,r]){let i=Ie(e),{values:a,keys:o}=this.ct(t,n,r);if(!Array.isArray(i))return this.ut=o,a;let s=this.ut??=[],c=[],l,u,d=0,f=i.length-1,p=0,m=a.length-1;for(;d<=f&&p<=m;)if(i[d]===null)d++;else if(i[f]===null)f--;else if(s[d]===o[p])c[p]=z(i[d],a[p]),d++,p++;else if(s[f]===o[m])c[m]=z(i[f],a[m]),f--,m--;else if(s[d]===o[m])c[m]=z(i[d],a[m]),R(e,c[m+1],i[d]),d++,m--;else if(s[f]===o[p])c[p]=z(i[f],a[p]),R(e,i[d],i[f]),f--,p++;else if(l===void 0&&(l=Re(o,p,m),u=Re(s,d,f)),l.has(s[d])){if(l.has(s[f])){let t=u.get(o[p]),n=t===void 0?null:i[t];if(n===null){let t=R(e,i[d]);z(t,a[p]),c[p]=t}else c[p]=z(n,a[p]),R(e,i[d],n),i[t]=null;p++}else Le(i[f]),f--}else Le(i[d]),d++;for(;p<=m;){let t=R(e,c[m+1]);z(t,a[p]),c[p++]=t}for(;d<=f;){let e=i[d++];e!==null&&Le(e)}return this.ut=o,Fe(e,c),T}}),Be=I(class extends L{constructor(e){if(super(e),e.type!==F.PROPERTY&&e.type!==F.ATTRIBUTE&&e.type!==F.BOOLEAN_ATTRIBUTE)throw Error("The `live` directive is not allowed on child or event bindings");if(!Me(e))throw Error("`live` bindings can only contain a single expression")}render(e){return e}update(e,[t]){if(t===T||t===E)return t;let n=e.element,r=e.name;if(e.type===F.PROPERTY){if(t===n[r])return T}else if(e.type===F.BOOLEAN_ATTRIBUTE){if(!!t===n.hasAttribute(r))return T}else if(e.type===F.ATTRIBUTE&&n.getAttribute(r)===t+``)return T;return Fe(e),t}}),B=(e,t)=>{var n,r;let i=e._$AN;if(i===void 0)return!1;for(let e of i)(r=(n=e)._$AO)==null||r.call(n,t,!1),B(e,t);return!0},V=e=>{let t,n;do{if((t=e._$AM)===void 0)break;n=t._$AN,n.delete(e),e=t}while(n?.size===0)},Ve=e=>{for(let t;t=e._$AM;e=t){let n=t._$AN;if(n===void 0)t._$AN=n=new Set;else if(n.has(e))break;n.add(e),We(t)}};function He(e){this._$AN===void 0?this._$AM=e:(V(this),this._$AM=e,Ve(this))}function Ue(e,t=!1,n=0){let r=this._$AH,i=this._$AN;if(i!==void 0&&i.size!==0){if(t){if(Array.isArray(r))for(let e=n;e<r.length;e++)B(r[e],!1),V(r[e]);else r!=null&&(B(r,!1),V(r))}else B(this,e)}}var We=e=>{var t,n;e.type==F.CHILD&&((t=e)._$AP??(t._$AP=Ue),(n=e)._$AQ??(n._$AQ=He))},Ge=class extends L{constructor(){super(...arguments),this._$AN=void 0}_$AT(e,t,n){super._$AT(e,t,n),Ve(this),this.isConnected=e._$AU}_$AO(e,t=!0){var n,r;e!==this.isConnected&&(this.isConnected=e,e?(n=this.reconnected)==null||n.call(this):(r=this.disconnected)==null||r.call(this)),t&&(B(this,e),V(this))}setValue(e){if(Me(this._$Ct))this._$Ct._$AI(e,this);else{let t=[...this._$Ct._$AH];t[this._$Ci]=e,this._$Ct._$AI(t,this,0)}}disconnected(){}reconnected(){}},Ke=()=>new qe,qe=class{},Je=new WeakMap,Ye=I(class extends Ge{render(e){return E}update(e,[t]){let n=t!==this.G;return n&&this.G!==void 0&&this.ot(void 0),(n||this.rt!==this.lt)&&(this.G=t,this.dt=e.options?.host,this.ot(this.lt=e.element)),E}ot(e){if(typeof this.G==`function`){let t=this.dt??globalThis,n=Je.get(t);n===void 0&&(n=new WeakMap,Je.set(t,n)),n.get(this.G)!==void 0&&this.G.call(this.dt,void 0),n.set(this.G,e),e!==void 0&&this.G.call(this.dt,e)}else this.G.value=e}get rt(){return typeof this.G==`function`?Je.get(this.dt??globalThis)?.get(this.G):this.G?.value}disconnected(){this.rt===this.lt&&this.ot(void 0)}reconnected(){this.ot(this.lt)}}),Xe=I(class extends L{constructor(e){if(super(e),e.type!==F.ATTRIBUTE||e.name!==`class`||e.strings?.length>2)throw Error("`classMap()` can only be used in the `class` attribute and must be the only part in the attribute.")}render(e){return` `+Object.keys(e).filter((t=>e[t])).join(` `)+` `}update(e,[t]){var n,r;if(this.it===void 0){this.it=new Set,e.strings!==void 0&&(this.nt=new Set(e.strings.join(` `).split(/\s/).filter((e=>e!==``))));for(let e in t)t[e]&&!((n=this.nt)!=null&&n.has(e))&&this.it.add(e);return this.render(t)}let i=e.element.classList;this.it.forEach((e=>{e in t||(i.remove(e),this.it.delete(e))}));for(let e in t){let n=!!t[e];n===this.it.has(e)||(r=this.nt)!=null&&r.has(e)||(n?(i.add(e),this.it.add(e)):(i.remove(e),this.it.delete(e)))}return T}}),Ze=typeof navigator<`u`&&navigator.userAgent.toLowerCase().indexOf(`firefox`)>0;function Qe(e,t,n){e.addEventListener?e.addEventListener(t,n,!1):e.attachEvent&&e.attachEvent(`on${t}`,function(){n(window.event)})}function $e(e,t){for(var n=t.slice(0,t.length-1),r=0;r<n.length;r++)n[r]=e[n[r].toLowerCase()];return n}function et(e){typeof e!=`string`&&(e=``),e=e.replace(/\s/g,``);for(var t=e.split(`,`),n=t.lastIndexOf(``);n>=0;)t[n-1]+=`,`,t.splice(n,1),n=t.lastIndexOf(``);return t}function tt(e,t){for(var n=e.length>=t.length?e:t,r=e.length>=t.length?t:e,i=!0,a=0;a<n.length;a++)r.indexOf(n[a])===-1&&(i=!1);return i}for(var nt={backspace:8,tab:9,clear:12,enter:13,return:13,esc:27,escape:27,space:32,left:37,up:38,right:39,down:40,del:46,delete:46,ins:45,insert:45,home:36,end:35,pageup:33,pagedown:34,capslock:20,num_0:96,num_1:97,num_2:98,num_3:99,num_4:100,num_5:101,num_6:102,num_7:103,num_8:104,num_9:105,num_multiply:106,num_add:107,num_enter:108,num_subtract:109,num_decimal:110,num_divide:111,"⇪":20,",":188,".":190,"/":191,"`":192,"-":Ze?173:189,"=":Ze?61:187,";":Ze?59:186,"'":222,"[":219,"]":221,"\\":220},H={"⇧":16,shift:16,"⌥":18,alt:18,option:18,"⌃":17,ctrl:17,control:17,"⌘":91,cmd:91,command:91},rt={16:`shiftKey`,18:`altKey`,17:`ctrlKey`,91:`metaKey`,shiftKey:16,ctrlKey:17,altKey:18,metaKey:91},U={16:!1,18:!1,17:!1,91:!1},W={},G=1;G<20;G++)nt[`f${G}`]=111+G;var K=[],it=`all`,at=[],ot=function(e){return nt[e.toLowerCase()]||H[e.toLowerCase()]||e.toUpperCase().charCodeAt(0)};function st(e){it=e||`all`}function q(){return it||`all`}function ct(){return K.slice(0)}function lt(e){var t=e.target||e.srcElement,n=t.tagName,r=!0;return(t.isContentEditable||(n===`INPUT`||n===`TEXTAREA`||n===`SELECT`)&&!t.readOnly)&&(r=!1),r}function ut(e){return typeof e==`string`&&(e=ot(e)),K.indexOf(e)!==-1}function dt(e,t){var n,r;for(var i in e||=q(),W)if(Object.prototype.hasOwnProperty.call(W,i))for(n=W[i],r=0;r<n.length;)n[r].scope===e?n.splice(r,1):r++;q()===e&&st(t||`all`)}function ft(e){var t=e.keyCode||e.which||e.charCode,n=K.indexOf(t);if(n>=0&&K.splice(n,1),e.key&&e.key.toLowerCase()===`meta`&&K.splice(0,K.length),(t===93||t===224)&&(t=91),t in U)for(var r in U[t]=!1,H)H[r]===t&&(J[r]=!1)}function pt(e){if(!e)Object.keys(W).forEach(function(e){return delete W[e]});else if(Array.isArray(e))e.forEach(function(e){e.key&&mt(e)});else if(typeof e==`object`)e.key&&mt(e);else if(typeof e==`string`){var t=[...arguments].slice(1),n=t[0],r=t[1];typeof n==`function`&&(r=n,n=``),mt({key:e,scope:n,method:r,splitKey:`+`})}}var mt=function(e){var t=e.key,n=e.scope,r=e.method,i=e.splitKey,a=i===void 0?`+`:i;et(t).forEach(function(e){var t=e.split(a),i=t.length,o=t[i-1],s=o===`*`?`*`:ot(o);if(W[s]){n||=q();var c=i>1?$e(H,t):[];W[s]=W[s].map(function(e){return(!r||e.method===r)&&e.scope===n&&tt(e.mods,c)?{}:e})}})};function ht(e,t,n){var r;if(t.scope===n||t.scope===`all`){for(var i in r=t.mods.length>0,U)Object.prototype.hasOwnProperty.call(U,i)&&(!U[i]&&t.mods.indexOf(+i)>-1||U[i]&&t.mods.indexOf(+i)===-1)&&(r=!1);(t.mods.length===0&&!U[16]&&!U[18]&&!U[17]&&!U[91]||r||t.shortcut===`*`)&&t.method(e,t)===!1&&(e.preventDefault?e.preventDefault():e.returnValue=!1,e.stopPropagation&&e.stopPropagation(),e.cancelBubble&&=!0)}}function gt(e){var t=W[`*`],n=e.keyCode||e.which||e.charCode;if(J.filter.call(this,e)){if((n===93||n===224)&&(n=91),K.indexOf(n)===-1&&n!==229&&K.push(n),[`ctrlKey`,`altKey`,`shiftKey`,`metaKey`].forEach(function(t){var n=rt[t];e[t]&&K.indexOf(n)===-1?K.push(n):!e[t]&&K.indexOf(n)>-1?K.splice(K.indexOf(n),1):t===`metaKey`&&e[t]&&K.length===3&&(e.ctrlKey||e.shiftKey||e.altKey||(K=K.slice(K.indexOf(n))))}),n in U){for(var r in U[n]=!0,H)H[r]===n&&(J[r]=!0);if(!t)return}for(var i in U)Object.prototype.hasOwnProperty.call(U,i)&&(U[i]=e[rt[i]]);e.getModifierState&&(!e.altKey||e.ctrlKey)&&e.getModifierState(`AltGraph`)&&(K.indexOf(17)===-1&&K.push(17),K.indexOf(18)===-1&&K.push(18),U[17]=!0,U[18]=!0);var a=q();if(t)for(var o=0;o<t.length;o++)t[o].scope===a&&(e.type===`keydown`&&t[o].keydown||e.type===`keyup`&&t[o].keyup)&&ht(e,t[o],a);if(n in W){for(var s=0;s<W[n].length;s++)if((e.type===`keydown`&&W[n][s].keydown||e.type===`keyup`&&W[n][s].keyup)&&W[n][s].key){for(var c=W[n][s],l=c.splitKey,u=c.key.split(l),d=[],f=0;f<u.length;f++)d.push(ot(u[f]));d.sort().join(``)===K.sort().join(``)&&ht(e,c,a)}}}}function _t(e){return at.indexOf(e)>-1}function J(e,t,n){K=[];var r=et(e),i=[],a=`all`,o=document,s=0,c=!1,l=!0,u=`+`;for(n===void 0&&typeof t==`function`&&(n=t),Object.prototype.toString.call(t)===`[object Object]`&&(t.scope&&(a=t.scope),t.element&&(o=t.element),t.keyup&&(c=t.keyup),t.keydown!==void 0&&(l=t.keydown),typeof t.splitKey==`string`&&(u=t.splitKey)),typeof t==`string`&&(a=t);s<r.length;s++)e=r[s].split(u),i=[],e.length>1&&(i=$e(H,e)),e=e[e.length-1],e=e===`*`?`*`:ot(e),e in W||(W[e]=[]),W[e].push({keyup:c,keydown:l,scope:a,mods:i,shortcut:r[s],method:n,key:r[s],splitKey:u});o!==void 0&&!_t(o)&&window&&(at.push(o),Qe(o,`keydown`,function(e){gt(e)}),Qe(window,`focus`,function(){K=[]}),Qe(o,`keyup`,function(e){gt(e),ft(e)}))}var vt={setScope:st,getScope:q,deleteScope:dt,getPressedKeyCodes:ct,isPressed:ut,filter:lt,unbind:pt};for(var yt in vt)Object.prototype.hasOwnProperty.call(vt,yt)&&(J[yt]=vt[yt]);if(typeof window<`u`){var bt=window.hotkeys;J.noConflict=function(e){return e&&window.hotkeys===J&&(window.hotkeys=bt),J},window.hotkeys=J}var Y=function(e,t,n,r){var i=arguments.length,a=i<3?t:r===null?r=Object.getOwnPropertyDescriptor(t,n):r,o;if(typeof Reflect==`object`&&typeof Reflect.decorate==`function`)a=Reflect.decorate(e,t,n,r);else for(var s=e.length-1;s>=0;s--)(o=e[s])&&(a=(i<3?o(a):i>3?o(t,n,a):o(t,n))||a);return i>3&&a&&Object.defineProperty(t,n,a),a},X=class extends j{constructor(){super(...arguments),this.placeholder=``,this.hideBreadcrumbs=!1,this.breadcrumbHome=`Home`,this.breadcrumbs=[],this._inputRef=Ke()}render(){let e=``;if(!this.hideBreadcrumbs){let t=[];for(let e of this.breadcrumbs)t.push(w`<button
            tabindex="-1"
            @click=${()=>this.selectParent(e)}
            class="breadcrumb"
          >
            ${e}
          </button>`);e=w`<div class="breadcrumb-list">
        <button
          tabindex="-1"
          @click=${()=>this.selectParent()}
          class="breadcrumb"
        >
          ${this.breadcrumbHome}
        </button>
        ${t}
      </div>`}return w`
      ${e}
      <div part="ninja-input-wrapper" class="search-wrapper">
        <input
          part="ninja-input"
          type="text"
          id="search"
          spellcheck="false"
          autocomplete="off"
          @input="${this._handleInput}"
          ${Ye(this._inputRef)}
          placeholder="${this.placeholder}"
          class="search"
        />
      </div>
    `}setSearch(e){this._inputRef.value&&(this._inputRef.value.value=e)}focusSearch(){requestAnimationFrame(()=>this._inputRef.value.focus())}_handleInput(e){let t=e.target;this.dispatchEvent(new CustomEvent(`change`,{detail:{search:t.value},bubbles:!1,composed:!1}))}selectParent(e){this.dispatchEvent(new CustomEvent(`setParent`,{detail:{parent:e},bubbles:!0,composed:!0}))}firstUpdated(){this.focusSearch()}_close(){this.dispatchEvent(new CustomEvent(`close`,{bubbles:!0,composed:!0}))}};X.styles=o`
    :host {
      flex: 1;
      position: relative;
    }
    .search {
      padding: 1.25em;
      flex-grow: 1;
      flex-shrink: 0;
      margin: 0px;
      border: none;
      appearance: none;
      font-size: 1.125em;
      background: transparent;
      caret-color: var(--ninja-accent-color);
      color: var(--ninja-text-color);
      outline: none;
      font-family: var(--ninja-font-family);
    }
    .search::placeholder {
      color: var(--ninja-placeholder-color);
    }
    .breadcrumb-list {
      padding: 1em 4em 0 1em;
      display: flex;
      flex-direction: row;
      align-items: stretch;
      justify-content: flex-start;
      flex: initial;
    }

    .breadcrumb {
      background: var(--ninja-secondary-background-color);
      text-align: center;
      line-height: 1.2em;
      border-radius: var(--ninja-key-border-radius);
      border: 0;
      cursor: pointer;
      padding: 0.1em 0.5em;
      color: var(--ninja-secondary-text-color);
      margin-right: 0.5em;
      outline: none;
      font-family: var(--ninja-font-family);
    }

    .search-wrapper {
      display: flex;
      border-bottom: var(--ninja-separate-border);
    }
  `,Y([N()],X.prototype,`placeholder`,void 0),Y([N({type:Boolean})],X.prototype,`hideBreadcrumbs`,void 0),Y([N()],X.prototype,`breadcrumbHome`,void 0),Y([N({type:Array})],X.prototype,`breadcrumbs`,void 0),X=Y([M(`ninja-header`)],X);var xt=class extends L{constructor(e){if(super(e),this.et=E,e.type!==F.CHILD)throw Error(this.constructor.directiveName+`() can only be used in child bindings`)}render(e){if(e===E||e==null)return this.ft=void 0,this.et=e;if(e===T)return e;if(typeof e!=`string`)throw Error(this.constructor.directiveName+`() called with a non-string value`);if(e===this.et)return this.ft;this.et=e;let t=[e];return t.raw=t,this.ft={_$litType$:this.constructor.resultType,strings:t,values:[]}}};xt.directiveName=`unsafeHTML`,xt.resultType=1;var St=I(xt);function*Ct(e,t){let n=typeof t==`function`;if(e!==void 0){let r=-1;for(let i of e)r>-1&&(yield n?t(r):t),r++,yield i}}function wt(e,t,n,r){var i=arguments.length,a=i<3?t:r===null?r=Object.getOwnPropertyDescriptor(t,n):r,o;if(typeof Reflect==`object`&&typeof Reflect.decorate==`function`)a=Reflect.decorate(e,t,n,r);else for(var s=e.length-1;s>=0;s--)(o=e[s])&&(a=(i<3?o(a):i>3?o(t,n,a):o(t,n))||a);return i>3&&a&&Object.defineProperty(t,n,a),a}var Tt=o`:host{font-family:var(--mdc-icon-font, "Material Icons");font-weight:normal;font-style:normal;font-size:var(--mdc-icon-size, 24px);line-height:1;letter-spacing:normal;text-transform:none;display:inline-block;white-space:nowrap;word-wrap:normal;direction:ltr;-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;-moz-osx-font-smoothing:grayscale;font-feature-settings:"liga"}`,Et=class extends j{render(){return w`<span><slot></slot></span>`}};Et.styles=[Tt],Et=wt([M(`mwc-icon`)],Et);var Dt=function(e,t,n,r){var i=arguments.length,a=i<3?t:r===null?r=Object.getOwnPropertyDescriptor(t,n):r,o;if(typeof Reflect==`object`&&typeof Reflect.decorate==`function`)a=Reflect.decorate(e,t,n,r);else for(var s=e.length-1;s>=0;s--)(o=e[s])&&(a=(i<3?o(a):i>3?o(t,n,a):o(t,n))||a);return i>3&&a&&Object.defineProperty(t,n,a),a},Z=class extends j{constructor(){super(),this.selected=!1,this.hotKeysJoinedView=!0,this.addEventListener(`click`,this.click)}ensureInView(){requestAnimationFrame(()=>this.scrollIntoView({block:`nearest`}))}click(){this.dispatchEvent(new CustomEvent(`actionsSelected`,{detail:this.action,bubbles:!0,composed:!0}))}updated(e){e.has(`selected`)&&this.selected&&this.ensureInView()}render(){let e;this.action.mdIcon?e=w`<mwc-icon part="ninja-icon" class="ninja-icon"
        >${this.action.mdIcon}</mwc-icon
      >`:this.action.icon&&(e=St(this.action.icon||``));let t;this.action.hotkey&&(t=this.hotKeysJoinedView?this.action.hotkey.split(`,`).map(e=>w`<div class="ninja-hotkey ninja-hotkeys">
            ${w`${Ct(e.split(`+`).map(e=>w`<kbd>${e}</kbd>`),`+`)}`}
          </div>`):this.action.hotkey.split(`,`).map(e=>w`<kbd class="ninja-hotkeys">${e.split(`+`).map(e=>w`<kbd class="ninja-hotkey">${e}</kbd>`)}</kbd>`));let n={selected:this.selected,"ninja-action":!0};return w`
      <div
        class="ninja-action"
        part="ninja-action ${this.selected?`ninja-selected`:``}"
        class=${Xe(n)}
      >
        ${e}
        <div class="ninja-title">${this.action.title}</div>
        ${t}
      </div>
    `}};Z.styles=o`
    :host {
      display: flex;
      width: 100%;
    }
    .ninja-action {
      padding: 0.75em 1em;
      display: flex;
      border-left: 2px solid transparent;
      align-items: center;
      justify-content: start;
      outline: none;
      transition: color 0s ease 0s;
      width: 100%;
    }
    .ninja-action.selected {
      cursor: pointer;
      color: var(--ninja-selected-text-color);
      background-color: var(--ninja-selected-background);
      border-left: 2px solid var(--ninja-accent-color);
      outline: none;
    }
    .ninja-action.selected .ninja-icon {
      color: var(--ninja-selected-text-color);
    }
    .ninja-icon {
      font-size: var(--ninja-icon-size);
      max-width: var(--ninja-icon-size);
      max-height: var(--ninja-icon-size);
      margin-right: 1em;
      color: var(--ninja-icon-color);
      margin-right: 1em;
      position: relative;
    }

    .ninja-title {
      flex-shrink: 0.01;
      margin-right: 0.5em;
      flex-grow: 1;
      font-size: 0.8125em;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .ninja-hotkeys {
      flex-shrink: 0;
      width: min-content;
      display: flex;
    }

    .ninja-hotkeys kbd {
      font-family: inherit;
    }
    .ninja-hotkey {
      background: var(--ninja-secondary-background-color);
      padding: 0.06em 0.25em;
      border-radius: var(--ninja-key-border-radius);
      text-transform: capitalize;
      color: var(--ninja-secondary-text-color);
      font-size: 0.75em;
      font-family: inherit;
    }

    .ninja-hotkey + .ninja-hotkey {
      margin-left: 0.5em;
    }
    .ninja-hotkeys + .ninja-hotkeys {
      margin-left: 1em;
    }
  `,Dt([N({type:Object})],Z.prototype,`action`,void 0),Dt([N({type:Boolean})],Z.prototype,`selected`,void 0),Dt([N({type:Boolean})],Z.prototype,`hotKeysJoinedView`,void 0),Z=Dt([M(`ninja-action`)],Z);var Ot=w` <div class="modal-footer" slot="footer">
  <span class="help">
    <svg
      version="1.0"
      class="ninja-examplekey"
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 1280 1280"
    >
      <path
        d="M1013 376c0 73.4-.4 113.3-1.1 120.2a159.9 159.9 0 0 1-90.2 127.3c-20 9.6-36.7 14-59.2 15.5-7.1.5-121.9.9-255 1h-242l95.5-95.5 95.5-95.5-38.3-38.2-38.2-38.3-160 160c-88 88-160 160.4-160 161 0 .6 72 73 160 161l160 160 38.2-38.3 38.3-38.2-95.5-95.5-95.5-95.5h251.1c252.9 0 259.8-.1 281.4-3.6 72.1-11.8 136.9-54.1 178.5-116.4 8.6-12.9 22.6-40.5 28-55.4 4.4-12 10.7-36.1 13.1-50.6 1.6-9.6 1.8-21 2.1-132.8l.4-122.2H1013v110z"
      />
    </svg>

    to select
  </span>
  <span class="help">
    <svg
      xmlns="http://www.w3.org/2000/svg"
      class="ninja-examplekey"
      viewBox="0 0 24 24"
    >
      <path d="M0 0h24v24H0V0z" fill="none" />
      <path
        d="M20 12l-1.41-1.41L13 16.17V4h-2v12.17l-5.58-5.59L4 12l8 8 8-8z"
      />
    </svg>
    <svg
      xmlns="http://www.w3.org/2000/svg"
      class="ninja-examplekey"
      viewBox="0 0 24 24"
    >
      <path d="M0 0h24v24H0V0z" fill="none" />
      <path d="M4 12l1.41 1.41L11 7.83V20h2V7.83l5.58 5.59L20 12l-8-8-8 8z" />
    </svg>
    to navigate
  </span>
  <span class="help">
    <span class="ninja-examplekey esc">esc</span>
    to close
  </span>
  <span class="help">
    <svg
      xmlns="http://www.w3.org/2000/svg"
      class="ninja-examplekey backspace"
      viewBox="0 0 20 20"
      fill="currentColor"
    >
      <path
        fill-rule="evenodd"
        d="M6.707 4.879A3 3 0 018.828 4H15a3 3 0 013 3v6a3 3 0 01-3 3H8.828a3 3 0 01-2.12-.879l-4.415-4.414a1 1 0 010-1.414l4.414-4.414zm4 2.414a1 1 0 00-1.414 1.414L10.586 10l-1.293 1.293a1 1 0 101.414 1.414L12 11.414l1.293 1.293a1 1 0 001.414-1.414L13.414 10l1.293-1.293a1 1 0 00-1.414-1.414L12 8.586l-1.293-1.293z"
        clip-rule="evenodd"
      />
    </svg>
    move to parent
  </span>
</div>`,kt=o`
  :host {
    --ninja-width: 640px;
    --ninja-backdrop-filter: none;
    --ninja-overflow-background: rgba(255, 255, 255, 0.5);
    --ninja-text-color: rgb(60, 65, 73);
    --ninja-font-size: 16px;
    --ninja-top: 20%;

    --ninja-key-border-radius: 0.25em;
    --ninja-accent-color: rgb(110, 94, 210);
    --ninja-secondary-background-color: rgb(239, 241, 244);
    --ninja-secondary-text-color: rgb(107, 111, 118);

    --ninja-selected-background: rgb(248, 249, 251);

    --ninja-icon-color: var(--ninja-secondary-text-color);
    --ninja-icon-size: 1.2em;
    --ninja-separate-border: 1px solid var(--ninja-secondary-background-color);

    --ninja-modal-background: #fff;
    --ninja-modal-shadow: rgb(0 0 0 / 50%) 0px 16px 70px;

    --ninja-actions-height: 300px;
    --ninja-group-text-color: rgb(144, 149, 157);

    --ninja-footer-background: rgba(242, 242, 242, 0.4);

    --ninja-placeholder-color: #8e8e8e;

    font-size: var(--ninja-font-size);

    --ninja-z-index: 1;
  }

  :host(.dark) {
    --ninja-backdrop-filter: none;
    --ninja-overflow-background: rgba(0, 0, 0, 0.7);
    --ninja-text-color: #7d7d7d;

    --ninja-modal-background: rgba(17, 17, 17, 0.85);
    --ninja-accent-color: rgb(110, 94, 210);
    --ninja-secondary-background-color: rgba(51, 51, 51, 0.44);
    --ninja-secondary-text-color: #888;

    --ninja-selected-text-color: #eaeaea;
    --ninja-selected-background: rgba(51, 51, 51, 0.44);

    --ninja-icon-color: var(--ninja-secondary-text-color);
    --ninja-separate-border: 1px solid var(--ninja-secondary-background-color);

    --ninja-modal-shadow: 0 16px 70px rgba(0, 0, 0, 0.2);

    --ninja-group-text-color: rgb(144, 149, 157);

    --ninja-footer-background: rgba(30, 30, 30, 85%);
  }

  .modal {
    display: none;
    position: fixed;
    z-index: var(--ninja-z-index);
    left: 0;
    top: 0;
    width: 100%;
    height: 100%;
    overflow: auto;
    background: var(--ninja-overflow-background);
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    -webkit-backdrop-filter: var(--ninja-backdrop-filter);
    backdrop-filter: var(--ninja-backdrop-filter);
    text-align: left;
    color: var(--ninja-text-color);
    font-family: var(--ninja-font-family);
  }
  .modal.visible {
    display: block;
  }

  .modal-content {
    position: relative;
    top: var(--ninja-top);
    margin: auto;
    padding: 0;
    display: flex;
    flex-direction: column;
    flex-shrink: 1;
    -webkit-box-flex: 1;
    flex-grow: 1;
    min-width: 0px;
    will-change: transform;
    background: var(--ninja-modal-background);
    border-radius: 0.5em;
    box-shadow: var(--ninja-modal-shadow);
    max-width: var(--ninja-width);
    overflow: hidden;
  }

  .bump {
    animation: zoom-in-zoom-out 0.2s ease;
  }

  @keyframes zoom-in-zoom-out {
    0% {
      transform: scale(0.99);
    }
    50% {
      transform: scale(1.01, 1.01);
    }
    100% {
      transform: scale(1, 1);
    }
  }

  .ninja-github {
    color: var(--ninja-keys-text-color);
    font-weight: normal;
    text-decoration: none;
  }

  .actions-list {
    max-height: var(--ninja-actions-height);
    overflow: auto;
    scroll-behavior: smooth;
    position: relative;
    margin: 0;
    padding: 0.5em 0;
    list-style: none;
    scroll-behavior: smooth;
  }

  .group-header {
    height: 1.375em;
    line-height: 1.375em;
    padding-left: 1.25em;
    padding-top: 0.5em;
    text-overflow: ellipsis;
    white-space: nowrap;
    overflow: hidden;
    font-size: 0.75em;
    line-height: 1em;
    color: var(--ninja-group-text-color);
    margin: 1px 0;
  }

  .modal-footer {
    background: var(--ninja-footer-background);
    padding: 0.5em 1em;
    display: flex;
    /* font-size: 0.75em; */
    border-top: var(--ninja-separate-border);
    color: var(--ninja-secondary-text-color);
  }

  .modal-footer .help {
    display: flex;
    margin-right: 1em;
    align-items: center;
    font-size: 0.75em;
  }

  .ninja-examplekey {
    background: var(--ninja-secondary-background-color);
    padding: 0.06em 0.25em;
    border-radius: var(--ninja-key-border-radius);
    color: var(--ninja-secondary-text-color);
    width: 1em;
    height: 1em;
    margin-right: 0.5em;
    font-size: 1.25em;
    fill: currentColor;
  }
  .ninja-examplekey.esc {
    width: auto;
    height: auto;
    font-size: 1.1em;
  }
  .ninja-examplekey.backspace {
    opacity: 0.7;
  }
`,Q=function(e,t,n,r){var i=arguments.length,a=i<3?t:r===null?r=Object.getOwnPropertyDescriptor(t,n):r,o;if(typeof Reflect==`object`&&typeof Reflect.decorate==`function`)a=Reflect.decorate(e,t,n,r);else for(var s=e.length-1;s>=0;s--)(o=e[s])&&(a=(i<3?o(a):i>3?o(t,n,a):o(t,n))||a);return i>3&&a&&Object.defineProperty(t,n,a),a},$=class extends j{constructor(){super(...arguments),this.placeholder=`Type a command or search...`,this.disableHotkeys=!1,this.hideBreadcrumbs=!1,this.openHotkey=`cmd+k,ctrl+k`,this.navigationUpHotkey=`up,shift+tab`,this.navigationDownHotkey=`down,tab`,this.closeHotkey=`esc`,this.goBackHotkey=`backspace`,this.selectHotkey=`enter`,this.hotKeysJoinedView=!1,this.noAutoLoadMdIcons=!1,this.data=[],this.visible=!1,this._bump=!0,this._actionMatches=[],this._search=``,this._flatData=[],this._headerRef=Ke()}open(e={}){this._bump=!0,this.visible=!0,this._headerRef.value.focusSearch(),this._actionMatches.length>0&&(this._selected=this._actionMatches[0]),this.setParent(e.parent)}close(){this._bump=!1,this.visible=!1}setParent(e){this._currentRoot=e||void 0,this._selected=void 0,this._search=``,this._headerRef.value.setSearch(``)}get breadcrumbs(){let e=[],t=this._selected?.parent;if(t)for(e.push(t);t;){let n=this._flatData.find(e=>e.id===t);n?.parent&&e.push(n.parent),t=n?n.parent:void 0}return e.reverse()}connectedCallback(){super.connectedCallback(),this.noAutoLoadMdIcons||document.fonts.load(`24px Material Icons`,`apps`).then(()=>{}),this._registerInternalHotkeys()}disconnectedCallback(){super.disconnectedCallback(),this._unregisterInternalHotkeys()}_flattern(e,t){let n=[];return e||=[],e.map(e=>{let r=e.children&&e.children.some(e=>typeof e==`string`),i={...e,parent:e.parent||t};return r?i:(i.children&&i.children.length&&(t=e.id,n=[...n,...i.children]),i.children=i.children?i.children.map(e=>e.id):[],i)}).concat(n.length?this._flattern(n,t):n)}update(e){e.has(`data`)&&!this.disableHotkeys&&(this._flatData=this._flattern(this.data),this._flatData.filter(e=>!!e.hotkey).forEach(e=>{J(e.hotkey,t=>{t.preventDefault(),e.handler&&e.handler(e)})})),super.update(e)}_registerInternalHotkeys(){this.openHotkey&&J(this.openHotkey,e=>{e.preventDefault(),this.visible?this.close():this.open()}),this.selectHotkey&&J(this.selectHotkey,e=>{this.visible&&(e.preventDefault(),this._actionSelected(this._actionMatches[this._selectedIndex]))}),this.goBackHotkey&&J(this.goBackHotkey,e=>{this.visible&&(this._search||(e.preventDefault(),this._goBack()))}),this.navigationDownHotkey&&J(this.navigationDownHotkey,e=>{this.visible&&(e.preventDefault(),this._selected=this._selectedIndex>=this._actionMatches.length-1?this._actionMatches[0]:this._actionMatches[this._selectedIndex+1])}),this.navigationUpHotkey&&J(this.navigationUpHotkey,e=>{this.visible&&(e.preventDefault(),this._selected=this._selectedIndex===0?this._actionMatches[this._actionMatches.length-1]:this._actionMatches[this._selectedIndex-1])}),this.closeHotkey&&J(this.closeHotkey,()=>{this.visible&&this.close()})}_unregisterInternalHotkeys(){this.openHotkey&&J.unbind(this.openHotkey),this.selectHotkey&&J.unbind(this.selectHotkey),this.goBackHotkey&&J.unbind(this.goBackHotkey),this.navigationDownHotkey&&J.unbind(this.navigationDownHotkey),this.navigationUpHotkey&&J.unbind(this.navigationUpHotkey),this.closeHotkey&&J.unbind(this.closeHotkey)}_actionFocused(e,t){this._selected=e,t.target.ensureInView()}_onTransitionEnd(){this._bump=!1}_goBack(){let e=this.breadcrumbs.length>1?this.breadcrumbs[this.breadcrumbs.length-2]:void 0;this.setParent(e)}render(){let e={bump:this._bump,"modal-content":!0},t={visible:this.visible,modal:!0},n=this._flatData.filter(e=>{let t=new RegExp(this._search,`gi`),n=e.title.match(t)||e.keywords?.match(t);return(!this._currentRoot&&this._search||e.parent===this._currentRoot)&&n}).reduce((e,t)=>e.set(t.section,[...e.get(t.section)||[],t]),new Map);this._actionMatches=[...n.values()].flat(),this._actionMatches.length>0&&this._selectedIndex===-1&&(this._selected=this._actionMatches[0]),this._actionMatches.length===0&&(this._selected=void 0);let r=e=>w` ${ze(e,e=>e.id,e=>w`<ninja-action
            exportparts="ninja-action,ninja-selected,ninja-icon"
            .selected=${Be(e.id===this._selected?.id)}
            .hotKeysJoinedView=${this.hotKeysJoinedView}
            @mouseover=${t=>this._actionFocused(e,t)}
            @actionsSelected=${e=>this._actionSelected(e.detail)}
            .action=${e}
          ></ninja-action>`)}`,i=[];return n.forEach((e,t)=>{let n=t?w`<div class="group-header">${t}</div>`:void 0;i.push(w`${n}${r(e)}`)}),w`
      <div @click=${this._overlayClick} class=${Xe(t)}>
        <div class=${Xe(e)} @animationend=${this._onTransitionEnd}>
          <ninja-header
            exportparts="ninja-input,ninja-input-wrapper"
            ${Ye(this._headerRef)}
            .placeholder=${this.placeholder}
            .hideBreadcrumbs=${this.hideBreadcrumbs}
            .breadcrumbs=${this.breadcrumbs}
            @change=${this._handleInput}
            @setParent=${e=>this.setParent(e.detail.parent)}
            @close=${this.close}
          >
          </ninja-header>
          <div class="modal-body">
            <div class="actions-list" part="actions-list">${i}</div>
          </div>
          <slot name="footer"> ${Ot} </slot>
        </div>
      </div>
    `}get _selectedIndex(){return this._selected?this._actionMatches.indexOf(this._selected):-1}_actionSelected(e){this.dispatchEvent(new CustomEvent(`selected`,{detail:{search:this._search,action:e},bubbles:!0,composed:!0})),e&&(e.children&&e.children?.length>0&&(this._currentRoot=e.id,this._search=``),this._headerRef.value.setSearch(``),this._headerRef.value.focusSearch(),e.handler&&(e.handler(e)?.keepOpen||this.close()),this._bump=!0)}async _handleInput(e){this._search=e.detail.search,await this.updateComplete,this.dispatchEvent(new CustomEvent(`change`,{detail:{search:this._search,actions:this._actionMatches},bubbles:!0,composed:!0}))}_overlayClick(e){e.target?.classList.contains(`modal`)&&this.close()}};$.styles=[kt],Q([N({type:String})],$.prototype,`placeholder`,void 0),Q([N({type:Boolean})],$.prototype,`disableHotkeys`,void 0),Q([N({type:Boolean})],$.prototype,`hideBreadcrumbs`,void 0),Q([N()],$.prototype,`openHotkey`,void 0),Q([N()],$.prototype,`navigationUpHotkey`,void 0),Q([N()],$.prototype,`navigationDownHotkey`,void 0),Q([N()],$.prototype,`closeHotkey`,void 0),Q([N()],$.prototype,`goBackHotkey`,void 0),Q([N()],$.prototype,`selectHotkey`,void 0),Q([N({type:Boolean})],$.prototype,`hotKeysJoinedView`,void 0),Q([N({type:Boolean})],$.prototype,`noAutoLoadMdIcons`,void 0),Q([N({type:Array,hasChanged(){return!0}})],$.prototype,`data`,void 0),Q([P()],$.prototype,`visible`,void 0),Q([P()],$.prototype,`_bump`,void 0),Q([P()],$.prototype,`_actionMatches`,void 0),Q([P()],$.prototype,`_search`,void 0),Q([P()],$.prototype,`_currentRoot`,void 0),Q([P()],$.prototype,`_flatData`,void 0),Q([P()],$.prototype,`breadcrumbs`,null),Q([P()],$.prototype,`_selected`,void 0),$=Q([M(`ninja-keys`)],$);export{$ as NinjaKeys};