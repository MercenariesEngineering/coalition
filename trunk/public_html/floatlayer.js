/////////////////////////////////////////////////////////////////////

var FloatLayers       = new Array();
var FloatLayersByName = new Array();

function addFloatLayer(n,offX,offY,spd){new FloatLayer(n,offX,offY,spd);}
function getFloatLayer(n){return FloatLayersByName[n];}
function alignFloatLayers(){for(var i=0;i<FloatLayers.length;i++)FloatLayers[i].align();}

function getXCoord(el) {
	x=0;
	while(el){
		x+=el.offsetLeft;
		el=el.offsetParent;
	}
	return x;
}
function getYCoord(el) {
	y=0;
	while(el){
		y+=el.offsetTop;
		el=el.offsetParent;
	}
	return y;
}

/////////////////////////////////////////////////////////////////////

FloatLayer.prototype.setFloatToTop=setTopFloater;
FloatLayer.prototype.setFloatToBottom=setBottomFloater;
FloatLayer.prototype.setFloatToLeft=setLeftFloater;
FloatLayer.prototype.setFloatToRight=setRightFloater;
FloatLayer.prototype.initialize=defineFloater;
FloatLayer.prototype.adjust=adjustFloater;
FloatLayer.prototype.align=alignFloater;

function FloatLayer(n, offX, offY, spd) {
	this.index=FloatLayers.length;

	FloatLayers.push(this);
	FloatLayersByName[n] = this;

	this.name    = n;
	this.floatX  = 0;
	this.floatY  = 0;
	this.tm      = null;
	this.steps   = spd;
	this.alignHorizontal=(offX>=0) ? leftFloater : rightFloater;
	this.alignVertical  =(offY>=0) ? topFloater : bottomFloater;
	this.ifloatX = Math.abs(offX);
	this.ifloatY = Math.abs(offY);
}

/////////////////////////////////////////////////////////////////////

function defineFloater(){
	this.layer  = document.getElementById(this.name);
	this.width  = this.layer.offsetWidth;
	this.height = this.layer.offsetHeight;
	this.prevX  = this.layer.offsetLeft;
	this.prevY  = this.layer.offsetTop;
}

function adjustFloater() {
	this.tm=null;
	if(this.layer.style.position!='absolute')return;

	var dx = Math.abs(this.floatX-this.prevX);
	var dy = Math.abs(this.floatY-this.prevY);

	if (dx < this.steps/2)
		cx = (dx>=1) ? 1 : 0;
	else
		cx = Math.round(dx/this.steps);

	if (dy < this.steps/2)
		cy = (dy>=1) ? 1 : 0;
	else
		cy = Math.round(dy/this.steps);

	if (this.floatX > this.prevX)
		this.prevX += cx;
	else if (this.floatX < this.prevX)
		this.prevX -= cx;

	if (this.floatY > this.prevY)
		this.prevY += cy;
	else if (this.floatY < this.prevY)
		this.prevY -= cy;

	this.layer.style.left = this.prevX;
	this.layer.style.top  = this.prevY;

	if (cx!=0||cy!=0){
		if(this.tm==null)this.tm=setTimeout('FloatLayers['+this.index+'].adjust()',50);
	}else
		alignFloatLayers();
}

function setLeftFloater(){this.alignHorizontal=leftFloater;}
function setRightFloater(){this.alignHorizontal=rightFloater;}
function setTopFloater(){this.alignVertical=topFloater;}
function setBottomFloater(){this.alignVertical=bottomFloater;}

function leftFloater(){this.floatX = document.body.scrollLeft + this.ifloatX;}
function topFloater(){this.floatY = document.body.scrollTop + this.ifloatY;}
function rightFloater(){this.floatX = document.body.scrollLeft + document.body.clientWidth - this.ifloatX - this.width;}
function bottomFloater(){this.floatY = document.body.scrollTop + document.body.clientHeight - this.ifloatY - this.height;}

function alignFloater(){
	if(this.layer==null)this.initialize();
	this.alignHorizontal();
	this.alignVertical();
	if(this.prevX!=this.floatX || this.prevY!=this.floatY){
		if(this.tm==null)this.tm=setTimeout('FloatLayers['+this.index+'].adjust()',50);
	}
}