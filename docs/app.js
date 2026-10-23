const viewer = document.querySelector('#viewer');
const form = document.querySelector('#controls');
const status = document.querySelector('#status');
const scene = new THREE.Scene(); scene.background = new THREE.Color(0x101318);
const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 1000); camera.position.set(95, 80, 120);
const renderer = new THREE.WebGLRenderer({ antialias: true }); viewer.append(renderer.domElement);
const controls = new THREE.OrbitControls(camera, renderer.domElement); controls.enableDamping = true;
scene.add(new THREE.HemisphereLight(0xffe0c0, 0x202838, 2));
const group = new THREE.Group(); scene.add(group); let triangles = [];

function resize() { renderer.setSize(viewer.clientWidth, viewer.clientHeight); camera.aspect = viewer.clientWidth / viewer.clientHeight; camera.updateProjectionMatrix(); }
window.addEventListener('resize', resize); resize();
function ring(R, cz, z, n) { const r = Math.sqrt(Math.max(0, R*R-(z-cz)**2)); return [...Array(n)].map((_,i)=>new THREE.Vector3(r*Math.cos(i*2*Math.PI/n), r*Math.sin(i*2*Math.PI/n), z)); }
function addQuad(a,b,c,d, out) { out.push(a,b,c,a,c,d); }
function shell(p) {
  const n=48, rows=24, ri=p.outer_radius-p.wall_thickness, outer=[], inner=[];
  for(let k=0;k<=rows;k++){const z=p.bottom_z+(p.top_z-p.bottom_z)*k/rows; outer.push(ring(p.outer_radius,p.center_z,z,n)); const iz=k===0?p.bottom_z+p.wall_thickness:z; inner.push(ring(ri,p.center_z,iz,n));}
  const v=[]; const f=[]; const add=(x)=>{const i=v.length;v.push(...x);return i};
  for(let k=0;k<rows;k++) for(let i=0;i<n;i++){const j=(i+1)%n, a=add([outer[k][i],outer[k][j],outer[k+1][j],outer[k+1][i]]);addQuad(...v.slice(a,a+4),f); const b=add([inner[k][i],inner[k+1][j],inner[k][j],inner[k+1][i]]);addQuad(...v.slice(b,b+4),f);}
  return {vertices:v,faces:f};
}
function stick(p, rng) {
  const z=p.bottom_z+2+ rng()*(p.top_z-p.bottom_z-4), br=Math.sqrt(Math.max(1,p.outer_radius**2-(z-p.center_z)**2));
  const tube=p.diameter_min/2+rng()*(p.diameter_max-p.diameter_min)/2, major=br*(p.scale_min+rng()*(p.scale_max-p.scale_min));
  const ext=major<br, d=ext?br-major-tube:major-tube-br, start=rng()*Math.PI*2, span=(20+rng()*50)*Math.PI/180, ns=10, nt=8, v=[], f=[];
  for(let i=0;i<=ns;i++)for(let j=0;j<nt;j++){const u=start+span*i/ns,w=2*Math.PI*j/nt;v.push(new THREE.Vector3((d+(major+tube*Math.cos(w))*Math.cos(u)),(major+tube*Math.cos(w))*Math.sin(u),z+tube*Math.sin(w)));}
  for(let i=0;i<ns;i++)for(let j=0;j<nt;j++){const a=i*nt+j,b=(i+1)*nt+j,c=(i+1)*nt+(j+1)%nt,d0=i*nt+(j+1)%nt;addQuad(v[a],v[b],v[c],v[d0],f)}
  return {vertices:v,faces:f};
}
function meshToGeometry(m){const pos=[]; for(const tri of m.faces) for(const q of tri) pos.push(q.x,q.y,q.z); const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));g.computeVertexNormals();return g;}
function generate(p){ group.clear(); triangles=[]; const bowl=shell(p); const material=new THREE.MeshStandardMaterial({color:0x9b542b,roughness:.9,side:THREE.DoubleSide}); group.add(new THREE.Mesh(meshToGeometry(bowl),material)); const rng=(()=>{let x=7;return()=>{x=(x*1664525+1013904223)>>>0;return x/4294967296}})(); for(let i=0;i<p.count;i++){const s=stick(p,rng);group.add(new THREE.Mesh(meshToGeometry(s),material));} status.textContent=`Generated ${p.count} sticks in the browser.`; }
function values(){const o=Object.fromEntries(new FormData(form)); for(const k in o)o[k]=Number(o[k]); return o;}
function stl(){let out='solid nest\n'; group.traverse(x=>{if(!x.isMesh)return;const a=x.geometry.attributes.position;for(let i=0;i<a.count;i+=3){const A=new THREE.Vector3().fromBufferAttribute(a,i),B=new THREE.Vector3().fromBufferAttribute(a,i+1),C=new THREE.Vector3().fromBufferAttribute(a,i+2),N=new THREE.Vector3().crossVectors(B.clone().sub(A),C.clone().sub(A)).normalize();out+=` facet normal ${N.x} ${N.y} ${N.z}\n  outer loop\n   vertex ${A.x} ${A.y} ${A.z}\n   vertex ${B.x} ${B.y} ${B.z}\n   vertex ${C.x} ${C.y} ${C.z}\n  endloop\n endfacet\n`;}}); return out+'endsolid nest\n';}
form.addEventListener('submit',e=>{e.preventDefault();generate(values())}); document.querySelector('#download').onclick=()=>{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([stl()],{type:'model/stl'}));a.download='nest_browser.stl';a.click();}; generate(values());
function animate(){requestAnimationFrame(animate);controls.update();renderer.render(scene,camera)} animate();
