
Module("xmlrpc","$Revision: 56 $",function(mod){
var xmlext=imprt("xml");
var urllib=imprt("urllib");
mod.InvalidServerResponse=Class(mod.Exception,function(publ,supr){
publ.__init__=function(status){
supr.__init__.call(this,"The server did not respond with a status 200 (OK) but with: "+status);
this.status=status;
};
publ.status;
});
mod.MalformedXmlRpc=Class(mod.Exception,function(publ,supr){
publ.__init__=function(msg,xml,trace){
supr.__init__.call(this,msg,trace);
this.xml=xml;
};
publ.xml;
});
mod.Fault=Class(mod.Exception,function(publ,supr){
publ.__init__=function(faultCode,faultString){
supr.__init__.call(this,"XML-RPC Fault: "+faultCode+"\n\n"+faultString);
this.faultCode=faultCode;
this.faultString=faultString;
};
publ.faultCode;
publ.faultString;
});
mod.marshall=function(obj){
if(obj.toXmlRpc!=null){
return obj.toXmlRpc();
}else{
var s="<struct>";for(var attr in obj){
if(typeof obj[attr]!="function"){
s+="<member><name>"+attr+"</name><value>"+mod.marshall(obj[attr])+"</value></member>";
}}s+="</struct>";
return s;
}
};
mod.unmarshall=function(xml){
try{
var doc=xmlext.parseXML(xml);
}catch(e){
throw new mod.MalformedXmlRpc("The server's response could not be parsed.",xml,e);
}
var rslt=mod.unmarshallDoc(doc,xml);
doc=null;
return rslt;
};
mod.unmarshallDoc=function(doc,xml){
try{
var node=doc.documentElement;
if(node==null){
throw new mod.MalformedXmlRpc("No documentElement found.",xml);
}
switch(node.tagName){
case "methodResponse":
return parseMethodResponse(node);
case "methodCall":
return parseMethodCall(node);
default:
throw new mod.MalformedXmlRpc("'methodCall' or 'methodResponse' element expected.\nFound: '"+node.tagName+"'",xml);
}
}catch(e){
if(e.constructor==mod.Fault){
throw e;
}else{
throw new mod.MalformedXmlRpc("Unmarshalling of XML failed.",xml,e);
}
}
};
var parseMethodResponse=function(node){
try{
for(var i=0;i<node.childNodes.length;i++){
var child=node.childNodes.item(i);
if(child.nodeType==1){
switch(child.tagName){
case "fault":
throw parseFault(child);
case "params":
var params=parseParams(child);
if(params.length==1){
return params[0];
}else{
throw new mod.MalformedXmlRpc("'params' element inside 'methodResponse' must have exactly ONE 'param' child element.\nFound: "+params.length);
}
default:
throw new mod.MalformedXmlRpc("'fault' or 'params' element expected.\nFound: '"+child.tagName+"'");
}
}
}
throw new mod.MalformedXmlRpc("No child elements found.");
}catch(e){
if(e.constructor==mod.Fault){
throw e;
}else{
throw new mod.MalformedXmlRpc("'methodResponse' element could not be parsed.",null,e);
}
}
};
var parseMethodCall=function(node){
try{
var methodName=null;
var params=new Array();
for(var i=0;i<node.childNodes.length;i++){
var child=node.childNodes.item(i);
if(child.nodeType==1){
switch(child.tagName){
case "methodName":
methodName=new String(child.firstChild.nodeValue);
break;
case "params":
params=parseParams(child);
break;
default:
throw new mod.MalformedXmlRpc("'methodName' or 'params' element expected.\nFound: '"+child.tagName+"'");
}
}
}
if(methodName==null){
throw new mod.MalformedXmlRpc("'methodName' element expected.");
}else{
return new Array(methodName,params);
}
}catch(e){
throw new mod.MalformedXmlRpc("'methodCall' element could not be parsed.",null,e);
}
};
var parseParams=function(node){
try{
var params=new Array();
for(var i=0;i<node.childNodes.length;i++){
var child=node.childNodes.item(i);
if(child.nodeType==1){
switch(child.tagName){
case "param":
params.push(parseParam(child));
break;
default:
throw new mod.MalformedXmlRpc("'param' element expected.\nFound: '"+child.tagName+"'");
}
}
}
return params;
}catch(e){
throw new mod.MalformedXmlRpc("'params' element could not be parsed.",null,e);
}
};
var parseParam=function(node){
try{
for(var i=0;i<node.childNodes.length;i++){
var child=node.childNodes.item(i);
if(child.nodeType==1){
switch(child.tagName){
case "value":
return parseValue(child);
default:
throw new mod.MalformedXmlRpc("'value' element expected.\nFound: '"+child.tagName+"'");
}
}
}
throw new mod.MalformedXmlRpc("'value' element expected.But none found.");
}catch(e){
throw new mod.MalformedXmlRpc("'param' element could not be parsed.",null,e);
}
};
var parseValue=function(node){
try{
for(var i=0;i<node.childNodes.length;i++){
var child=node.childNodes.item(i);
if(child.nodeType==1){
switch(child.tagName){
case "string":
var s="";
for(var j=0;j<child.childNodes.length;j++){
s+=new String(child.childNodes.item(j).nodeValue);
}
return s;
case "int":
case "i4":
case "double":
return(child.firstChild)?Number(child.firstChild.nodeValue):0;
case "boolean":
return Boolean(isNaN(parseInt(child.firstChild.nodeValue))?(child.firstChild.nodeValue=="true"):parseInt(child.firstChild.nodeValue));
case "base64":
return parseBase64(child);
case "dateTime.iso8601":
return parseDateTime(child);
case "array":
return parseArray(child);
case "struct":
return parseStruct(child);
case "nil":
return null;
default:
throw new mod.MalformedXmlRpc("'string','int','i4','double','boolean','base64','dateTime.iso8601','array' or 'struct' element expected.\nFound: '"+child.tagName+"'");
}
}
}
if(node.firstChild){
var s="";
for(var j=0;j<node.childNodes.length;j++){
s+=new String(node.childNodes.item(j).nodeValue);
}
return s;
}else{
return "";
}
}catch(e){
throw new mod.MalformedXmlRpc("'value' element could not be parsed.",null,e);
}
};
var parseBase64=function(node){
try{
var s=node.firstChild.nodeValue;
return s.decode("base64");
}catch(e){
throw new mod.MalformedXmlRpc("'base64' element could not be parsed.",null,e);
}
};
var parseDateTime=function(node){
try{
if(/^(\d{4})-?(\d{2})-?(\d{2})T(\d{2}):?(\d{2}):?(\d{2})/.test(node.firstChild.nodeValue)){
return new Date(Date.UTC(RegExp.$1,RegExp.$2-1,RegExp.$3,RegExp.$4,RegExp.$5,RegExp.$6));}else{
throw new mod.MalformedXmlRpc("Could not convert the given date.");
}
}catch(e){
throw new mod.MalformedXmlRpc("'dateTime.iso8601' element could not be parsed.",null,e);
}
};
var parseArray=function(node){
try{
for(var i=0;i<node.childNodes.length;i++){
var child=node.childNodes.item(i);
if(child.nodeType==1){
switch(child.tagName){
case "data":
return parseData(child);
default:
throw new mod.MalformedXmlRpc("'data' element expected.\nFound: '"+child.tagName+"'");
}
}
}
throw new mod.MalformedXmlRpc("'data' element expected. But not found.");
}catch(e){
throw new mod.MalformedXmlRpc("'array' element could not be parsed.",null,e);
}
};
var parseData=function(node){
try{
var rslt=new Array();
for(var i=0;i<node.childNodes.length;i++){
var child=node.childNodes.item(i);
if(child.nodeType==1){
switch(child.tagName){
case "value":
rslt.push(parseValue(child));
break;
default:
throw new mod.MalformedXmlRpc("'value' element expected.\nFound: '"+child.tagName+"'");
}
}
}
return rslt;
}catch(e){
throw new mod.MalformedXmlRpc("'data' element could not be parsed.",null,e);
}
};
var parseStruct=function(node){
try{
var struct=new Object();
for(var i=0;i<node.childNodes.length;i++){
var child=node.childNodes.item(i);
if(child.nodeType==1){
switch(child.tagName){
case "member":
var member=parseMember(child);
if(member[0]!=""){
struct[member[0]]=member[1];
}
break;
default:
throw new mod.MalformedXmlRpc("'data' element expected.\nFound: '"+child.tagName+"'");
}
}
}
return struct;
}catch(e){
throw new mod.MalformedXmlRpc("'struct' element could not be parsed.",null,e);
}
};
var parseMember=function(node){
try{
var name="";
var value=null;
for(var i=0;i<node.childNodes.length;i++){
var child=node.childNodes.item(i);
if(child.nodeType==1){
switch(child.tagName){
case "value":
value=parseValue(child);
break;
case "name":
if(child.hasChildNodes()){
name=new String(child.firstChild.nodeValue);
}
break;
default:
throw new mod.MalformedXmlRpc("'value' or 'name' element expected.\nFound: '"+child.tagName+"'");
}
}
}
return[name,value];
}catch(e){
throw new mod.MalformedXmlRpc("'member' element could not be parsed.",null,e);
}
};
var parseFault=function(node){
try{
for(var i=0;i<node.childNodes.length;i++){
var child=node.childNodes.item(i);
if(child.nodeType==1){
switch(child.tagName){
case "value":
var flt=parseValue(child);
return new mod.Fault(flt.faultCode,flt.faultString);
default:
throw new mod.MalformedXmlRpc("'value' element expected.\nFound: '"+child.tagName+"'");
}
}
}
throw new mod.MalformedXmlRpc("'value' element expected. But not found.");
}catch(e){
throw new mod.MalformedXmlRpc("'fault' element could not be parsed.",null,e);
}
};
mod.XMLRPCMethod=Class(function(publ){
var postData=function(url,user,pass,data,callback){
if(callback==null){
var rslt=urllib.postURL(url,user,pass,data,[["Content-Type","text/xml"]]);
return rslt;
}else{
return urllib.postURL(url,user,pass,data,[["Content-Type","text/xml"]],callback);
}
};
var handleResponse=function(resp){
var status=null;
try{
status=resp.status;
}catch(e){
}
if(status==200){
var respDoc=null;
try{
respDoc=resp.responseXML;
}catch(e){
}
var respTxt="";
try{
respTxt=resp.responseText;
}catch(e){
}
if((respDoc==null)||(respDoc.documentElement==null)){
if(respTxt==null||respTxt==""){
throw new mod.MalformedXmlRpc("The server responded with an empty document.","");
}else{
return mod.unmarshall(respTxt);
}
}else{
return mod.unmarshallDoc(respDoc,respTxt);
}
}else{
throw new mod.InvalidServerResponse(status);
}
};
var getXML=function(methodName,args){
var data='<?xml version="1.0"?><methodCall><methodName>'+methodName+'</methodName>';
if(args.length>0){
data+="<params>";
for(var i=0;i<args.length;i++){data+='<param><value>'+mod.marshall(args[i])+'</value></param>';}
data+='</params>';
}data+='</methodCall>';
return data;
};
publ.__init__=function(url,methodName,user,pass){
this.methodName=methodName;
this.url=url;
this.user=user;
this.password=pass;
};
publ.__call__=function(){
if(typeof arguments[arguments.length-1]!='function'){
var data=getXML(this.methodName,arguments);
var resp=postData(this.url,this.user,this.password,data);
return handleResponse(resp);
}else{
var args=new Array();
for(var i=0;i<arguments.length;i++){
args.push(arguments[i]);
}
var cb=args.pop();
var data=getXML(this.methodName,args);
return postData(this.url,this.user,this.password,data,function(resp){
var rslt=null;
var exc=null;
try{
rslt=handleResponse(resp);
}catch(e){
exc=e;
}
try{
cb(rslt,exc);
}catch(e){
}
args=null;
resp=null;
});
}
};
publ.toMulticall=function(){
var multiCallable=new Object();
multiCallable.methodName=this.methodName;
var params=[];
for(var i=0;i<arguments.length;i++){
params[i]=arguments[i];
}
multiCallable.params=params;
return multiCallable;
};
publ.setAuthentication=function(user,pass){
this.user=user;
this.password=pass;
};
publ.methodName;
publ.url;
publ.user;
publ.password;
});
mod.ServiceProxy=Class(function(publ){
publ.__init__=function(url,methodNames,user,pass){
if(methodNames instanceof Array){
if(methodNames.length>0){
var tryIntrospection=false;
}else{
var tryIntrospection=true;
}
}else{
pass=user;
user=methodNames;
methodNames=[];
var tryIntrospection=true;
}
this._url=url;
this._user=user;
this._password=pass;
this._addMethodNames(methodNames);
if(tryIntrospection){
try{
this._introspect();
}catch(e){
}
}
};
publ._addMethodNames=function(methodNames){
for(var i=0;i<methodNames.length;i++){
var obj=this;
var names=methodNames[i].split(".");
for(var n=0;n<names.length-1;n++){
var name=names[n];
if(obj[name]){
obj=obj[name];
}else{
obj[name]=new Object();
obj=obj[name];
}
}
var name=names[names.length-1];
if(obj[name]){
}else{
var mth=new mod.XMLRPCMethod(this._url,methodNames[i],this._user,this._password);
obj[name]=mth;
this._methods.push(mth);
}
}
};
publ._setAuthentication=function(user,pass){
this._user=user;
this._password=pass;
for(var i=0;i<this._methods.length;i++){
this._methods[i].setAuthentication(user,pass);
}
};
publ._introspect=function(){
this._addMethodNames(["system.listMethods","system.methodHelp","system.methodSignature"]);
var m=this.system.listMethods();
this._addMethodNames(m);
};
publ._url;
publ._user;
publ._password;
publ._methods=new Array();
});
mod.ServerProxy=mod.ServiceProxy;
String.prototype.toXmlRpc=function(){return "<string>"+this.replace(/&/g,"&amp;").replace(/</g,"&lt;")+"</string>";};
Number.prototype.toXmlRpc=function(){if(this==parseInt(this)){
return "<int>"+this+"</int>";}else if(this==parseFloat(this)){return "<double>"+this+"</double>";}else{return false.toXmlRpc();}};Boolean.prototype.toXmlRpc=function(){if(this==true){
return "<boolean>1</boolean>";
}else{
return "<boolean>0</boolean>";
}};Date.prototype.toXmlRpc=function(){
var padd=function(s,p){
s=p+s;
return s.substring(s.length-p.length);
};
var y=padd(this.getUTCFullYear(),"0000");
var m=padd(this.getUTCMonth()+1,"00");
var d=padd(this.getUTCDate(),"00");var h=padd(this.getUTCHours(),"00");var min=padd(this.getUTCMinutes(),"00");var s=padd(this.getUTCSeconds(),"00");
var ms=padd(this.getUTCMilliseconds(),"000");var isodate=y+m+d+"T"+h+":"+min+":"+s+":"+ms;
return "<dateTime.iso8601>"+isodate+"</dateTime.iso8601>";};Array.prototype.toXmlRpc=function(){var retstr="<array><data>";for(var i=0;i<this.length;i++){retstr+="<value>"+mod.marshall(this[i])+"</value>";}return retstr+"</data></array>";};mod.__main__=function(){
var s=new mod.ServiceProxy("http://jsolait.net/test.py",['echo']);
print("creating ServiceProxy object using introspection for method construction...\n");
print("%s created\n".format(s));
print("creating and marshalling test data:\n");
var o=[1.234,5,{a:"Hello & < ",b:new Date()}];
print(mod.marshall(o));
print("\ncalling echo() on remote service...\n");
var r=s.echo(o);
print("service returned data(marshalled again):\n");
print(mod.marshall(r));
};
});
