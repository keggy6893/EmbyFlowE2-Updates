Add-Type -AssemblyName System.Drawing
Add-Type -ReferencedAssemblies System.Drawing -TypeDefinition @'
using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.IO;
public class SourcePicons {
 static Graphics g; static Color c;
 static void Line(float x,float y,float a,float b,float w=4){using(var p=new Pen(c,w)){p.StartCap=LineCap.Round;p.EndCap=LineCap.Round;g.DrawLine(p,x,y,a,b);}}
 static void Circle(float x,float y,float r,float w=4){using(var p=new Pen(c,w))g.DrawEllipse(p,x-r,y-r,2*r,2*r);}
 static void Dot(float x,float y,float r=3){using(var b=new SolidBrush(c))g.FillEllipse(b,x-r,y-r,2*r,2*r);}
 static GraphicsPath Rounded(float x,float y,float w,float h,float r){var p=new GraphicsPath();p.AddArc(x,y,r*2,r*2,180,90);p.AddArc(x+w-2*r,y,2*r,2*r,270,90);p.AddArc(x+w-2*r,y+h-2*r,2*r,2*r,0,90);p.AddArc(x,y+h-2*r,2*r,2*r,90,90);p.CloseFigure();return p;}
 static void Rect(float x,float y,float w,float h,float r=6){using(var p=new Pen(c,4))using(var q=Rounded(x,y,w,h,r))g.DrawPath(p,q);}
 static void Disk(){Rect(27,20,59,88);Circle(56,53,16);Dot(56,53,5);Dot(39,94);Dot(74,94);}
 static void USB(){Line(95,95,95,47);Circle(95,39,5,3);Line(95,71,109,61);Line(109,61,109,50);Rect(105,42,8,8,1);Line(95,85,84,75);Dot(83,72,4);Line(95,98,91,104);Line(91,104,99,104);Line(99,104,95,98);}
 static void NAS(){Rect(21,24,70,80);Line(56,27,56,101,3);Line(31,39,45,39);Line(66,39,80,39);Dot(38,90);Dot(73,90);}
 static void Search(){using(var b=new SolidBrush(Color.FromArgb(255,12,24,39)))g.FillEllipse(b,66,58,46,46);Circle(89,81,22);Line(105,98,119,112,6);}
 static void Address(){using(var b=new SolidBrush(Color.FromArgb(255,12,24,39)))g.FillRectangle(b,73,66,43,46);Rect(74,65,43,46,6);for(int y=0;y<2;y++)for(int x=0;x<2;x++){Line(84+x*20,77+y*20,90+x*20,77+y*20,3);Line(87+x*20,74+y*20,87+x*20,80+y*20,3);}}
 static void Folder(){Line(18,95,18,34);Line(18,34,47,34);Line(47,34,57,44);Line(57,44,109,44);Line(109,44,109,72);Line(18,95,77,95);var state=g.Save();g.TranslateTransform(65,69);g.RotateTransform(-43);Rect(-21,-7,29,14,7);Rect(-5,-7,29,14,7);g.Restore(state);using(var b=new SolidBrush(Color.FromArgb(255,12,24,39)))g.FillEllipse(b,82,82,34,34);Circle(99,99,17);Line(91,99,97,105);Line(97,105,108,93);}
 static void Network(){Rect(51,18,26,24,4);Line(64,44,64,65);Line(25,65,103,65);Line(25,65,25,80);Line(64,65,64,80);Line(103,65,103,80);Rect(12,82,26,24,4);Rect(51,82,26,24,4);Rect(90,82,26,24,4);}
 public static void Build(string dir){Directory.CreateDirectory(dir);string[] names={"disk_usb","nas_search","nas_address","folder_link","disk","usb","network"};foreach(string n in names){using(var hi=new Bitmap(384,384)){g=Graphics.FromImage(hi);g.SmoothingMode=SmoothingMode.AntiAlias;g.Clear(Color.Transparent);g.ScaleTransform(3,3);c=ColorTranslator.FromHtml(n=="folder_link"?"#55E898":n=="nas_address"||n=="network"?"#51D7E8":n=="disk"||n=="disk_usb"?"#AC78F5":"#4DAAFF");if(n=="disk_usb"){Disk();USB();}else if(n=="nas_search"){NAS();Search();}else if(n=="nas_address"){NAS();Address();}else if(n=="folder_link")Folder();else if(n=="disk")Disk();else if(n=="usb"){Rect(44,34,38,70,6);Rect(50,16,26,20,2);Line(57,23,57,29,3);Line(69,23,69,29,3);Dot(63,84,5);}else Network();g.Dispose();using(var output=new Bitmap(128,128)){using(var og=Graphics.FromImage(output)){og.InterpolationMode=InterpolationMode.HighQualityBicubic;og.DrawImage(hi,0,0,128,128);}output.Save(Path.Combine(dir,n+".png"),ImageFormat.Png);}}}}
}
'@
[SourcePicons]::Build((Join-Path $PSScriptRoot 'source_picons_v1'))
