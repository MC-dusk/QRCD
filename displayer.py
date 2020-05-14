import qrcd
import re
from flask import *

app=Flask(__name__)
app.debug=True

qrc_line_re=re.compile(r'^\[(\d+),(\d+)\](.*)$')
qrc_chunk_re=re.compile(r'^(.*)\((\d+),(\d+)$')

@app.route('/',methods=['GET','POST'])
def search():
    if request.method=='GET':
        return render_template('search.html')
    else:
        return render_template('search.html',
            result=list(qrcd.query_lyric(request.form['name'],request.form['singer']))
        )

@app.route('/play/<int:songid>')
def play(songid):
    return render_template('player.html',songid=songid)

@app.route('/api/get_lyric/<int:songid>')
def api_get_lyric(songid):
    lrc=qrcd.fetch_lyric_by_id(songid,['orig','roma','ts'])

    def parse_qrc(data):
        INF=2147483647

        line_src=[]
        chunk_src=[]
        line_action=[]
        chunk_action=[]

        def apply_chunk(data,time_s,dt):
            chunkid=len(chunk_src)
            line_src[-1].append(chunkid)
            chunk_src.append(data)
            if time_s is not None:
                chunk_action.append([time_s,True,chunkid])
                chunk_action.append([time_s+dt,False,chunkid])

        line_src.append([])
        line_action.append([-INF,False,0])
        line_action.append([INF,True,0])
        chunk_action.append([-INF,False,0])
        chunk_action.append([INF,True,0])
        chunk_src.append(None)

        for line_s in data.split('\n'):
            line=qrc_line_re.match(line_s)
            if not line:
                print('ignored LINE:',line_s)
                continue

            time_s,dt,content=line.groups()
            time_s=int(time_s)
            dt=int(dt)
            lineid=len(line_src)
            line_src.append([])

            line_action.append([time_s,True,lineid])
            line_action.append([time_s+dt,False,lineid])

            splited_content=content.split(')')
            for ind,chunk_s in enumerate(splited_content):
                chunk=qrc_chunk_re.match(chunk_s)
                if not chunk:
                    if len(splited_content)==ind+1: # last chunk without timestamp
                        if chunk_s:
                            apply_chunk(chunk_s,None,None)
                    else: # notmal ')'
                        splited_content[ind+1]=chunk_s+')'+splited_content[ind+1]
                    continue

                content,time_s,dt=chunk.groups()
                time_s=int(time_s)
                dt=int(dt)
                apply_chunk(content,time_s,dt)

        line_action.sort(key=lambda x:x[0])
        chunk_action.sort(key=lambda x:x[0])

        return {
            'line_src': line_src,
            'chunk_src': chunk_src,
            'line_action': line_action,
            'chunk_action': chunk_action,
        }

    return jsonify(
        orig=parse_qrc(lrc['orig']),
        roma=parse_qrc(lrc['roma']),
        ts=parse_qrc(lrc['ts']),
    )

app.run('0.0.0.0',80)