
Module("xml","$Revision: 55 $",function(mod){
mod.XMLNS="http://www.w3.org/2000/xmlns/";
mod.NSXML="http://www.w3.org/XML/1998/namespace";
mod.nsPrefixMap={"http://www.w3.org/2000/xmlns/":"xmlns","http://www.w3.org/XML/1998/namespace":"xml"};
mod.NoXMLParser=Class(mod.Exception,function(publ,supr){
publ.__init__=function(trace){
supr.__init__.call(this,"Could not create an XML parser.",trace);
};
});
mod.ParsingFailed=Class(mod.Exception,function(publ,supr){
publ.__init__=function(xml,trace){
supr.__init__.call(this,"Failed parsing XML document.",trace);
this.xml=xml;
};
publ.xml;
});
mod.parseXML=function(xml){
var obj=null;
var isMoz=false;
var isIE=false;
var isASV=false;
try{
var p=window.parseXML;
if(p==null){
throw "No ASV paseXML";
}
isASV=true;
}catch(e){
try{
obj=new DOMParser();
isMoz=true;
}catch(e){
try{
obj=new ActiveXObject("Msxml2.DomDocument.4.0");isIE=true;
}catch(e){
try{
obj=new ActiveXObject("Msxml2.DomDocument");isIE=true;
}catch(e){
try{
obj=new ActiveXObject("microsoft.XMLDOM");isIE=true;}catch(e){
throw new mod.NoXMLParser(e);
}
}
}
}
}
try{
if(isMoz){
obj=obj.parseFromString(xml,"text/xml");
return obj;
}else if(isIE){
obj.loadXML(xml);
return obj;
}else if(isASV){
return window.parseXML(xml,null);
}
}catch(e){
throw new mod.ParsingFailed(xml,e);
}
};
mod.importNode=function(importedNode,deep){deep=(deep==null)?true:deep;
var ELEMENT_NODE=1;var ATTRIBUTE_NODE=2;var TEXT_NODE=3;var CDATA_SECTION_NODE=4;var ENTITY_REFERENCE_NODE=5;var ENTITY_NODE=6;var PROCESSING_INSTRUCTION_NODE=7;var COMMENT_NODE=8;var DOCUMENT_NODE=9;var DOCUMENT_TYPE_NODE=10;var DOCUMENT_FRAGMENT_NODE=11;var NOTATION_NODE=12;var importChildren=function(srcNode,parent){if(deep){for(var i=0;i<srcNode.childNodes.length;i++){
var n=mod.importNode(srcNode.childNodes.item(i),true);parent.appendChild(n);}}};var node=null;switch(importedNode.nodeType){case ATTRIBUTE_NODE:node=document.createAttributeNS(importedNode.namespaceURI,importedNode.nodeName);node.value=importedNode.value;
break;case DOCUMENT_FRAGMENT_NODE:node=document.createDocumentFragment();importChildren(importedNode,node);break;case ELEMENT_NODE:node=document.createElementNS(importedNode.namespaceURI,importedNode.tagName);for(var i=0;i<importedNode.attributes.length;i++){
var attr=this.importNode(importedNode.attributes.item(i),deep);node.setAttributeNodeNS(attr);}importChildren(importedNode,node);break;case ENTITY_REFERENCE_NODE:node=importedNode;break;case PROCESSING_INSTRUCTION_NODE:node=document.createProcessingInstruction(importedNode.target,importedNode.data);break;case TEXT_NODE:case CDATA_SECTION_NODE:case COMMENT_NODE:node=document.createTextNode(importedNode.nodeValue);break;case DOCUMENT_NODE:case DOCUMENT_TYPE_NODE:case NOTATION_NODE:case ENTITY_NODE:throw "not supported in DOM2";break;}return node;};
var getNSPrefix=function(node,namespaceURI,nsPrefixMap){
if(!namespaceURI){
return "";
}else if(mod.nsPrefixMap[namespaceURI]){
return mod.nsPrefixMap[namespaceURI]+":";
}else if(nsPrefixMap[namespaceURI]!=null){
return nsPrefixMap[namespaceURI]+":";
}
if(node.nodeType==1){
for(var i=0;i<node.attributes.length;i++){
var attr=node.attributes.item(i);if(attr.namespaceURI==mod.XMLNS&&attr.value==namespaceURI){
return attr.localName+":";
}
}
}else{
throw new Error("Cannot find a namespace prefix for "+namespaceURI);
}
if(node.parentNode){
return getNSPrefix(node.parentNode,namespaceURI,nsPrefixMap);}else{
throw new Error("Cannot find a namespace prefix for "+namespaceURI);
}
};
mod.node2XML=function(node,nsPrefixMap,attrParent){
nsPrefixMap=(nsPrefixMap==null)?{}:nsPrefixMap;var ELEMENT_NODE=1;var ATTRIBUTE_NODE=2;var TEXT_NODE=3;var CDATA_SECTION_NODE=4;var ENTITY_REFERENCE_NODE=5;var ENTITY_NODE=6;var PROCESSING_INSTRUCTION_NODE=7;var COMMENT_NODE=8;var DOCUMENT_NODE=9;var DOCUMENT_TYPE_NODE=10;var DOCUMENT_FRAGMENT_NODE=11;var NOTATION_NODE=12;var s="";switch(node.nodeType){case ATTRIBUTE_NODE:
try{
var nsprefix=getNSPrefix(attrParent,node.namespaceURI,nsPrefixMap);
}catch(e){
alert(node.namespaceURI+"\n"+e.message);
}
var localName=node.localName;if(typeof localName=='undefined'){localName=node.name;}if(nsprefix+localName=="xmlns:xmlns"){nsprefix="";}s+=nsprefix+localName+'="'+node.value+'"';break;case DOCUMENT_NODE:
if(node.documentElement!=null){
s+=this.node2XML(node.documentElement,nsPrefixMap);
}
break;case ELEMENT_NODE:
s+="<"+node.tagName;
for(var i=0;i<node.attributes.length;i++){
s+=" "+this.node2XML(node.attributes.item(i),nsPrefixMap,node);}if(node.childNodes.length==0){s+="/>\n";}else{s+=">";for(var child=node.firstChild;child!=null;child=child.nextSibling){s+=this.node2XML(child,nsPrefixMap);}
s+="</"+node.tagName+">\n";
}break;case PROCESSING_INSTRUCTION_NODE:s+="<?"+node.target+" "+node.data+" ?>";break;case TEXT_NODE:s+=node.nodeValue;break;case CDATA_SECTION_NODE:s+="<"+"![CDATA["+node.nodeValue+"]"+"]>";break;case COMMENT_NODE:s+="<!--"+node.nodeValue+"-->";break;
case ENTITY_REFERENCE_NODE:case DOCUMENT_FRAGMENT_NODE:case DOCUMENT_TYPE_NODE:case NOTATION_NODE:case ENTITY_NODE:throw new mod.Exception("Nodetype(%s) not supported.".format(node.nodeType));break;}return s;};
});
