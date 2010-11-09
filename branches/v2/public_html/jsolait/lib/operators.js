
Module("operators","$Revision: 20 $",function(mod){
mod.lt=function(a,b){
if((a!=null)&&(a.__lt__!==undefined)){
return a.__lt__(b);
}else if((b!=null)&&(b.__lt__!==undefined)){
return b.__lt__(a);
}else{
return a<b;
}
};mod.le=function(a,b){
if((a!=null)&&(a.__le__!==undefined)){
return a.__le__(b);
}else if((b!=null)&&(b.__le__!==undefined)){
return b.__le__(a);
}else{
return a<=b;
}
};mod.eq=function(a,b){
if((a!=null)&&(a.__eq__!==undefined)){
return a.__eq__(b);
}else if((b!=null)&&(b.__eq__!==undefined)){
return b.__eq__(a);
}else{
return a===b;
}
};
mod.ne=function(a,b){
if((a!=null)&&(a.__ne__!==undefined)){
return a.__ne__(b);
}else if((b!=null)&&(b.__ne__!==undefined)){
return b.__ne__(a);
}else{
return a!==b;
}
};mod.is=function(a,b){
if((a!=null)&&(a.__is__!==undefined)){
return a.__is__(b);
}else if((b!=null)&&(b.__is__!==undefined)){
return b.__is__(a);
}else{
return a===b;
}
};
mod.isnot=function(a,b){
if((a!=null)&&(a.__isnot__!==undefined)){
return a.__isnot__(b);
}else if((b!=null)&&(b.__isnot__!==undefined)){
return b.__isnot__(a);
}else{
return a!==b;
}
};
mod.ge=function(a,b){
if((a!=null)&&(a.__ge__!==undefined)){
return a.__ge__(b);
}else if((b!=null)&&(b.__ge__!==undefined)){
return b.__ge__(a);
}else{
return a>=b;
}
};mod.gt=function(a,b){
if((a!=null)&&(a.__gt__!==undefined)){
return a.__gt__(b);
}else if((b!=null)&&(b.__gt__!==undefined)){
return b.__gt__(a);
}else{
return a>b;
}
};mod.not=function(a){
if((a!=null)&&(a.__not__!==undefined)){
return a.__not__();
}else{
return!a;
}
};
Array.prototype.__eq__=function(a){
if(this.length!=a.length){
return false;
}else{
for(var i=0;i<this.length;i++){
if(!mod.eq(this[i],a[i])){
return false;
}
}
return true;
}
};
Array.prototype.__neq__=function(a){
if(this.length!=a.length){
return true;
}else{
for(var i=0;i<this.length;i++){
if(mod.neq(this[i],a[i])){
return true;
}
}
return false;
}
};
mod.__main__=function(){
};
});
