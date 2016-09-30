//window.theoplayer = window.theoplayer || {};
//window.theoplayer.configuration = window.theoplayer.configuration || {};

//window.theoplayer.configuration.libraryLocation = window.theoplayer.configuration.libraryLocation || 'http://yourcdn.com/theoplayer/';
//window.theoplayer.configuration.styleSheetURI = window.theoplayer.configuration.styleSheetURI || 'http://yourcdn.com/theoplayer/style/theoplayer.css';

/*!
THEOplayer

Usage of this software is limited by the THEOplayer License
The license is available at:
http://www.theoplayer.com/license.html

It is prohibited to reverse engineer, decompile, translate,
disassemble, decipher, decrypt, or otherwise attempt to 
discover the source code of this software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

For more information, visit http://www.theoplayer.com or contact
contact @ theoplayer . com

THEOplayer is based on a patent pending technology developed by 
OpenTelly (http://www.opentelly.com).

Version: 1.6.37
Created: Tue May 24 2016 15:21:05 GMT+0200 (Romance Daylight Time)
*/

(function (self) {var _=["string","canplay","canplaythrough","dimensionsChanged","durationchange","ended","error","emptied","fullscreenchange","initialized","loadeddata","loadedmetadata","loadstart","playing","progress","ratechange","resize","seeked","seeking","stalled","timeupdate","volumechange","waiting","timedmetadata","unsupportedPlatform","online","offline","played","aspectRatio","autoplay","buffered","currentFrame","currentProgramDateTime","currentSrc","currentTime","duration","element","frameAccurateSeekEnabled","frameRate","fullscreenEnabled","height","paused","playbackRate","poster","textTracks","videoWidth","videoHeight","volume","warning","startTime","endTime","startFrame","endFrame","videoTracks","audioTracks","//cdn.theoplayer.com/1.6.37/c5692bfe-c2a2-4b87-a160-5e1c57e4a16a/","theoplayer.js","script","theoplayer-loaded","WARNING: THEOplayer is not initialised yet.","video { opacity : 0; }"],$=["prototype","addEventListener","indexOf","removeEventListener","dispatchEvent","exitFullscreen","requestFullscreen","defineProperty","constructor","theoplayer","configuration","libraryLocation","createElement","appendChild","removeChild","contains","innerHTML","controller","document","location","navigator","setTimeout","clearTimeout","setInterval","clearInterval","TypeError","SyntaxError","parseInt","parseFloat","Uint8Array","WorkerGlobalScope","XMLHttpRequest"];!function(e,t,n,r,a,i,o,l,s,c,u,f,d){!function(){function t(e){i(e,0)}var r=function(){function e(){}return e[$[0]].ja=function(e){return this.ka=this.ka||{},void 0===this.ka[e]&&(this.ka[e]=[]),this.ka[e]},e[$[0]][$[1]]=function(e,t){var n=this.ja(e),r=n[$[2]](t);-1===r&&n.push(t)},e[$[0]][$[3]]=function(e,t){var n=this.ja(e),r=n[$[2]](t);t?-1!==r&&n.splice(r,1):n.length=0},e[$[0]].la=function(){this.ka=null},e[$[0]][$[4]]=function(e,n){if(n)return t(this[$[4]].bind(this,e));_[0]==typeof e&&(e={type:e});for(var r=this.ja(e.type).slice(),a=0,i=r;a<i.length;a++){var o=i[a];o.call(this,e)}},e}(),a=function(e){var t=function(e){var t=this,n=[_[1],_[2],_[3],_[4],_[5],_[6],_[7],_[8],_[9],_[10],_[11],_[12],"pause","play",_[13],_[14],_[15],_[16],_[17],_[18],_[19],_[20],_[21],_[22],_[23],_[24],_[25],_[26]],r=function(e){t[$[4]](e,!0)},a=function(e){var t;for(t=0;t<n.length;t+=1)e[$[1]](n[t],r)},i=function(e){var t;for(t=0;t<n.length;t+=1)e[$[3]](n[t],r)};e[$[1]]&&a(e),t.ma={na:function(t){e[$[3]]&&i(e),e=t,e[$[1]]&&a(e)},oa:function(){return e}},t[$[5]]=function(){return e[$[5]].apply(e,arguments)},t.load=function(){return e.load.apply(e,arguments)},t.play=function(){return e.play.apply(e,arguments)},t.pause=function(){return e.pause.apply(e,arguments)},t[$[6]]=function(){return e[$[6]].apply(e,arguments)},t[$[5]]=function(){return e[$[5]].apply(e,arguments)},function(){var n,r=[_[27],_[28],_[29],_[30],_[31],_[32],_[33],_[34],_[35],"dvr",_[36],_[5],_[6],_[37],_[38],_[39],_[40],_[9],"live","loop","muted",_[41],_[42],_[43],_[18],"src",_[44],_[45],_[46],_[47],_[48],"width",_[49],_[50],_[51],_[52],_[25],_[53],_[54]],a=function(n){d[$[7]](t,n,{get:function(){return e[n]},set:function(t){return e[n]=t}})};for(n=0;n<r.length;n+=1)a(r[n])}()};t[$[0]]=new r,t[$[0]][$[8]]=t;var n={},a=new t(e),i=a.ma;return n.pa=a,n.ma=i,delete a.ma,n},o=function(e,t){"use strict";var n=t.head,r=e[$[9]],i=r&&r[$[10]]||{},o=r&&r.onReady||void 0,l=(i&&i[$[11]]||_[55])+_[56],s=t[$[12]]("style"),c=t[$[12]](_[57]),u=n[$[13]].bind(n),f=_[58],d=[],p=function(){console.log(_[59])},y=function(){e[$[3]](f,y),n[$[14]](s)},h=function(e){var t;for(t=0;t<d.length;t+=1)if(d[t].ji[$[15]](e))return d[t];return!1},r=function(e,t){var n=h(e);return n?n.pa:(n=new a({exitFullscreen:p,load:p,play:p,pause:p,requestFullscreen:p}),n.ji=e,n.rc=t,d.push(n),e.id&&(d[e.id]=n),n.pa)};return s[$[16]]=_[60],u(s),e[$[1]](f,y),e[$[9]]=r,r.Mv=d,r[$[10]]=i,r.onReady=o,r.player=p,r[$[17]]=p,r.destroy=p,c.async=!0,c.src=l,u(c),r}(e,n);return o}()}(self,self.window,self[$[18]],self[$[19]],self[$[20]],self[$[21]],self[$[22]],self[$[23]],self[$[24]],self.Error,self[$[25]],self[$[26]],self.Object,self.Math,self[$[27]],self[$[28]],self.isNaN,self[$[29]],self.Worker,self[$[30]],self[$[31]]);}(self));