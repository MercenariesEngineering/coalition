
Module("forms","$Revision: 5 $",function(mod){
mod.Form=Class(function(publ,supr){
publ.elements=[];
publ.action="";
publ.method="GET";
publ.__init__=function(action,method){
this.elements=[];
this.action=(action==null)?"":action;
this.method=(method==null)?"GET":method;
};
publ.set=function(name,value){
var f=null;
for(var i=0;i<this.elements;i++){
if(name==this.elements[i].name){
f=this.elements[i];
f.value=value;
}
}
if(f==null){
f=new mod.Element(name,value);
this.elements.push(f);
}
if(this[name]==null){
this[name]=f;
}
return f;
};
publ.encode=function(){
var data=[];
for(var i=0;i<this.elements.length;i++){
data.push(this.elements[i].encode());
}
return data.join("&");
};
publ.queryString=function(){
return this.action+"?"+this.encode();
};
publ.submit=function(){
if(this.method.toLowerCase()=="get"){
try{
location.href=this.queryString();
}catch(e){
try{
var s='location="'+this.queryString().replace(/(["\\])/g,'\\$1')+'"';
browserEval(encodeURI(s));}catch(e){
throw "Cannot set new location.";
}
}
}else{
var frm=document.createElement("form");
frm.setAttribute("action",this.action);
frm.setAttribute("method",this.method);
document.getElementsByTagName("body")[0].appendChild(frm);
for(var i=0;i<this.elements.length;i++){
var elem=this.elements[i];
var inp=document.createElement("input");
inp.setAttribute("type","hidden");
inp.setAttribute("name",elem.name);
inp.setAttribute("value",elem.value);
frm.appendChild(inp);
}
frm.submit();
}
};
publ.submitNoReload=function(callback){
if(this.action&&this.method){
var urllib=imprt("urllib");
switch(this.method.toLowerCase()){
case "get":
return urllib.getURL(this.queryString(),[["Content-Type","application/x-www-form-urlencoded"]],callback);
break;
case "post":
return urllib.postURL(this.action,this.encode(),[["Content-Type","application/x-www-form-urlencoded"]],callback);
break;
default:
throw "Method can only be POST or GET but is: "+this.method;
}
}else{
throw "No action and/or method defined";
}
};
});
mod.Element=Class(function(publ,supr){
publ.name="";
publ.value="";
publ.__init__=function(name,value){
this.name=name;
this.value=value;
};
publ.encode=function(){
return encodeURIComponent(this.name)+"="+encodeURIComponent(this.value);
};
});mod.__main__=function(){
var fm=new mod.Form("http://localhost/echoform.py","get");
print("testing all sorts of chars, the should be encoded.");
fm.set("testchars","abcdefghijklmnopqrstuvwxyz1234567890 \n\t!@#$%^&*()_+-=[]{};'\\:\"|,./<>?");
print(fm.encode());
try{
print(fm.submitNoReload().responseText);
}catch(e){
print(e);
}
fm.method="post";
print(fm.submitNoReload().responseText);
};
});
