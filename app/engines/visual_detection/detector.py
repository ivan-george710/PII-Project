"""Adapted from ivan-george710/PII-Project faces.py (see assets/ATTRIBUTION.md).

CPU YuNet, bounded frames, rotation passes, overlapping tiles and padded boxes.
No foreign pipeline/contracts, face recognition or demographic classifiers.
"""
from hashlib import sha256
from pathlib import Path
from threading import Lock
from math import isfinite
import numpy as np
from .images import decode

MODEL_SHA256='8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4'


class FaceDetectionError(RuntimeError):pass


def same_face(a,b):
    ax,ay,aw,ah=a;bx,by,bw,bh=b
    overlap=max(0,min(ax+aw,bx+bw)-max(ax,bx))*max(0,min(ay+ah,by+bh)-max(ay,by))
    small,large=sorted((aw*ah,bw*bh))
    return overlap/max(aw*ah+bw*bh-overlap,1e-9)>.35 or (overlap/max(small,1e-9)>.8 and large/max(small,1e-9)<2.5)


class FaceDetector:
    def __init__(self,model_path=None):
        try:
            import cv2
            self.cv2=cv2
            path=Path(model_path) if model_path else Path(__file__).parent/'assets/face_detection_yunet_2023mar.onnx'
            if sha256(path.read_bytes()).hexdigest()!=MODEL_SHA256:raise ValueError()
            self.model=cv2.FaceDetectorYN.create(str(path),'',(320,320),.35,.3,5000,
                cv2.dnn.DNN_BACKEND_OPENCV,cv2.dnn.DNN_TARGET_CPU)
            self.lock=Lock()
        except Exception:raise FaceDetectionError('Required local face model is unavailable or untrusted.') from None

    def detect(self,data,source_metadata=None):
        try:
            with decode(data,frame='raw') as image:rgb=np.array(image)
            candidates=[]
            for rotation in range(4):
                rotated=np.ascontiguousarray(np.rot90(rgb,rotation));rh,rw=rotated.shape[:2]
                tiles=[(0,0,rw,rh)]
                if rotation==0 and max(rw,rh)>=600:
                    tiles.extend((int(x*rw),int(y*rh),min(rw,int((x+.45)*rw)),min(rh,int((y+.45)*rh)))
                                 for y in (0,.275,.55) for x in (0,.275,.55))
                for x0,y0,x1,y1 in tiles:
                    crop=rotated[y0:y1,x0:x1];ch,cw=crop.shape[:2];factor=min(1,1280/max(cw,ch))
                    frame=self.cv2.resize(crop,(max(1,round(cw*factor)),max(1,round(ch*factor))))
                    with self.lock:
                        self.model.setInputSize((frame.shape[1],frame.shape[0]))
                        _,faces=self.model.detect(self.cv2.cvtColor(frame,self.cv2.COLOR_RGB2BGR))
                    for face in faces if faces is not None else ():
                        fx,fy,fw,fh=map(float,face[:4]);score=float(face[-1])
                        if not all(isfinite(v) for v in (fx,fy,fw,fh,score)) or not 0<=score<=1 or fw<=0 or fh<=0:
                            raise ValueError('Invalid detector result')
                        corners=[((x0+fx/factor)/rw,(y0+fy/factor)/rh),((x0+(fx+fw)/factor)/rw,(y0+(fy+fh)/factor)/rh)]
                        points=[((x,y),(1-y,x),(1-x,1-y),(y,1-x))[rotation] for x,y in corners]
                        xs,ys=zip(*points);left,top=max(0,min(xs)),max(0,min(ys));right,bottom=min(1,max(xs)),min(1,max(ys))
                        if right>left and bottom>top:candidates.append(((left,top,right-left,bottom-top),score))
            unique=[]
            for box,score in sorted(candidates,key=lambda c:-c[1]):
                if not any(same_face(box,old) for old,_ in unique):unique.append((box,score))
            result=[]
            for (x,y,w,h),score in sorted(unique,key=lambda c:(c[0][1],c[0][0])):
                left=max(0,x-.08*w);top=max(0,y-.12*h)
                result.append((list((left,top,min(1,x+1.08*w)-left,min(1,y+1.12*h)-top)),score))
            return result
        except Exception:raise FaceDetectionError('Local face inspection could not complete.') from None
