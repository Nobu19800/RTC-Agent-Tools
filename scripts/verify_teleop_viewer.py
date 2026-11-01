"""Verify HTTP assets and the native WebSocket binary stream; no GPU render claim."""
import asyncio
import json
import os
from pathlib import Path
import urllib.request
import websockets


async def main():
    run=Path(os.environ['RUN_DIR'])
    report={}
    for name,path in [('index','/index.html'),('viewerModule','/src/public/drone_viewer.js'),
                      ('pduManager','/thirdparty/hakoniwa-pdu-javascript/src/PduManager.js'),
                      ('pduCodec','/thirdparty/hakoniwa-pdu-javascript/src/pdu_msgs/std_msgs/pdu_conv_UInt32.js'),
                      ('floorModel','/assets/models/base-floor.glb'),
                      ('droneModel','/assets/models/base-drone-frame.glb')]:
        with urllib.request.urlopen('http://127.0.0.1:8000'+path,timeout=5) as response:
            raw=response.read()
            assert response.status==200 and raw
            report[name]=dict(status=200,bytes=len(raw))
    async with websockets.connect('ws://127.0.0.1:8765',open_timeout=5,close_timeout=3) as socket:
        frames=[]
        for _ in range(3):
            data=await asyncio.wait_for(socket.recv(),5)
            assert isinstance(data,bytes) and len(data)>32768,(type(data),len(data))
            frames.append(len(data))
        report['binaryFrameLengths']=frames
    report['passed']=True
    report['scope']='HTTP modules and live native WebSocket binary frames, not a browser WebGL render test'
    (run/'viewer-stream-result.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS: HTTP assets and three live WebSocket binary frames',frames)


if __name__=='__main__': asyncio.run(main())
