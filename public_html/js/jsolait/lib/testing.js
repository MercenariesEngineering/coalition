
Module("testing","$Revision: 51 $",function(mod){
var ops=imprt('operators');
mod.minProfileTime=500;
mod.timeExec=function(repeat,fn){
var args=[];
for(var i=2;i<arguments.length;i++){
args.push(arguments[i]);
}
var t=(new Date()).getTime();
for(var i=0;i<=repeat;i++){
fn.apply(null,args);
}
return((new Date()).getTime()-t)/(repeat+1);
};
mod.profile=function(min,fn){
if(arguments.length==1){
fn=min;
min=mod.minProfileTime;
}
var args=[];
for(var i=2;i<arguments.length;i++){
args.push(arguments[i]);
}
var cnt=0;
var t1=(new Date()).getTime();
t2=t1;
while(t2-t1<min){
cnt++;
fn.apply(null,args);
t2=(new Date()).getTime();
}
return(t2-t1)/cnt;
};
mod.Test=Class(function(publ,supr){
publ.__init__=function(name,testScope){
if(testScope===undefined){
testScope=name;
name='anonymous';
}
this.name=name;
this.testScope=testScope;
};
publ.run=function(){
this.failed=false;
this.error=null;
this.startTime=(new Date()).getTime();
try{
this.testScope();
}catch(e){
if(e.constructor==mod.AssertFailed){
this.error=e;
this.failed=true;
}else{
throw new mod.Exception("Failed to run test.",e);
}
}
this.endTime=(new Date()).getTime();
this.duration=this.endTime-this.startTime;
};
publ.report=function(){
if(this.error){
return "Test '%s' has failed after %s ms due to:\n\n%s".format(this.name,this.duration,this.error.toTraceString().indent(4));
}else{
return "Test '%s' completed in %s ms".format(this.name,this.duration);
}
};
publ.failed=false;
publ.error;
publ.startTime;
publ.endTime;
publ.duration;
});
mod.test=function(name,testScope){
if(arguments.length==1){
testScope=name;
name='anonymous';
}
var t=new mod.Test(name,testScope);
t.run();
return t.report();
};
mod.AssertFailed=Class(mod.Exception,function(publ,supr){
publ.__init__=function(comment,failMsg){
this.failMessage=failMsg;
this.comment=comment;
supr.__init__.call(this,"%s failed: %s".format(comment,failMsg));
};
});
mod.assert=function(comment,value,failMsg){
if(typeof comment=='boolean'){
failMsg=value;
value=comment;
comment='';
}
if(value!==true){
throw new mod.AssertFailed(comment,failMsg===undefined?"Expected true but found: %s".format(repr(value)):failMsg);
}};
mod.assertTrue=function(comment,value){
if(arguments.length==1){
value=comment;
comment='';
}
mod.assert(comment,value===true,"Expected true but found: %s".format(repr(value)));
};
mod.assertFalse=function(comment,value){
if(arguments.length==1){
value=comment;
comment='';
}
mod.assert(comment,value===false,"Expected false but found: %s".format(repr(value)));};
mod.assertEquals=function(comment,value1,value2){
if(arguments.length==2){
value2=value1;
value1=comment;
comment='';
}
mod.assert(comment,ops.eq(value1,value2),"Expected %s === %s.".format(repr(value1),repr(value2)));
};
mod.assertNotEquals=function(comment,value1,value2){
if(arguments.length==2){
value2=value1;
value1=comment;
comment='';
}
mod.assert(comment,ops.ne(value1,value2),"Expected %s !== %s.".format(repr(value1),repr(value2)));
};
mod.assertIs=function(comment,value1,value2){
if(arguments.length==2){
value2=value1;
value1=comment;
comment='';
}
mod.assert(comment,ops.is(value1,value2),"Expected %s === %s.".format(repr(value1),repr(value2)));
};
mod.assertIsNot=function(comment,value1,value2){
if(arguments.length==2){
value2=value1;
value1=comment;
comment='';
}
mod.assert(comment,ops.isnot(value1,value2),"Expected %s !== %s.".format(repr(value1),repr(value2)));
};
mod.assertNull=function(comment,value){
if(arguments.length==1){
value=comment;
comment='';
}
mod.assert(comment,value===null,"Expected %s === null.".format(repr(value)));};
mod.assertNotNull=function(comment,value){
if(arguments.length==1){
value=comment;
comment='';
}
mod.assert(comment,value!==null,"Expected %s !== null.".format(repr(value)));};
mod.assertUndefined=function(comment,value){
if(arguments.length==1){
value=comment;
comment='';
}
mod.assert(comment,value===undefined,"Expected %s === undefined.".format(repr(value)));
};
mod.assertNotUndefined=function(comment,value){
if(arguments.length==1){
value=comment;
comment='';
}
mod.assert(comment,value!==undefined,"Expected %s !== undefined".format(repr(value)));};
mod.assertNaN=function(comment,value){
if(arguments.length==1){
value=comment;
comment='';
}
mod.assert(comment,isNaN(value)===true,"Expected %s === NaN.".format(repr(value)));};
mod.assertNotNaN=function(comment,value){
if(arguments.length==1){
value=comment;
comment='';
}
mod.assert(comment,isNaN(value)!==true,"Expected %s !== NaN".format(repr(value)));
};
mod.fail=function(comment){
throw new mod.AssertFailed(comment,"Fail was called");
};
mod.objectKeys=function(obj){
var keys=[];
for(var n in obj){
keys.push(n);
}
return keys;
};});
