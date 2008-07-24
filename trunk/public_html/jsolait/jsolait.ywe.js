
include(typeof JsolaitInstallPath=='undefined'?"./jsolait/jsolait.js":JsolaitInstallPath);
jsolait.__imprt__=function(name){
if(jsolait.modules[name]){
return jsolait.modules[name];
}else{
var src,modPath;
var searchURIs=[];
if(jsolait.knownModuleURIs[name]!=undefined){
searchURIs.push(jsolait.knownModuleURIs[name].format(jsolait));
}else{
name=name.split('.');
if(name.length>1){
if(jsolait.knownModuleURIs[name[0]]!=undefined){
var uri=jsolait.knownModuleURIs[name[0]].format(jsolait);
searchURIs.push("%s/%s.js".format(uri,name.slice(1).join('/')));
}
searchURIs.push("%s/%s.js".format(jsolait.packagesURI.format(jsolait),name.join('/')));
}
for(var i=0;i<jsolait.moduleSearchURIs.length;i++){
searchURIs.push("%s/%s.js".format(jsolait.moduleSearchURIs[i].format(jsolait),name.join("/")));
}
name=name.join(".");
}
var failedURIs=[];
for(var i=0;i<searchURIs.length;i++){
try{
include(searchURIs[i]);
if(jsolait.modules[name]!=null){
return jsolait.modules[name];
}else{
throw new jsolait.ImportFailed(name,failedURIs,new jsolait.Exception("Module did not register itself and cannot be imported. "+name));
}
break;
}catch(e){
failedURIs.push(searchURIs[i]);
}
}
throw new jsolait.ImportFailed(name,failedURIs,new jsolait.Exception("Module source could not be included. "+name));
}
};
