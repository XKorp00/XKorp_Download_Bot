from cProfile import run
import pstats
from pyobigram.utils import sizeof_fmt,get_file_size,createID,nice_time
from pyobigram.client import ObigramClient,inlineQueryResultArticle
from MoodleClient import MoodleClient

from JDatabase import JsonDatabase
import zipfile
import os
import infos
import xdlink
import mediafire
import datetime
import time
import requests
from bs4 import BeautifulSoup
import youtube
import NexCloudClient
from pydownloader.downloader import Downloader
from ProxyCloud import ProxyCloud
import ProxyCloud
import socket
import tlmedia
import S5Crypto
import asyncio
import aiohttp
import moodlews
import moodle_client
from moodle_client import MoodleClient2
from yarl import URL
import re
from draft_to_calendar import send_calendar

def sign_url(token: str, url: URL):
    query: dict = dict(url.query)
    query["token"] = token
    path = "webservice" + url.path
    return url.with_path(path).with_query(query)

def short_url(url):
    api = 'https://shortest.link/es/'
    resp = requests.post(api,data={'url':url})
    if resp.status_code == 200:
        soup = BeautifulSoup(resp.text,'html.parser')
        shorten = soup.find('input',{'class':'short-url'})['value']
        return shorten
    return url

def downloadFile(downloader,filename,currentBits,totalBits,speed,time,args):
    try:
        bot = args[0]
        message = args[1]
        thread = args[2]
        if thread.getStore('stop'):
            downloader.stop()
        name = filename
        nam = name[0:15]
        zip = str(name).split('.')[-1]
        name2 = nam+'.'+zip
        if '7z' in name:     
            name2 = nam+'.7z.'+zip
        filename = name2   
        downloadingInfo = infos.createDownloading(filename,totalBits,currentBits,speed,time,tid=thread.id)
        bot.editMessageText(message,downloadingInfo)
    except Exception as ex: print(str(ex))
    pass

def uploadFile(filename,currentBits,totalBits,speed,time,args):
    try:
        bot = args[0]
        message = args[1]
        originalfile = args[2]
        thread = args[3]
        name = filename
        nam = name[0:15]
        zip = str(name).split('.')[-1]
        name2 = nam+'.'+zip
        if '7z' in name:     
            name2 = nam+'.7z.'+zip
        filename = name2   
        downloadingInfo = infos.createUploading(filename,totalBits,currentBits,speed,time,originalfile)
        bot.editMessageText(message,downloadingInfo)
    except Exception as ex: print(str(ex))
    pass

def processUploadFiles(filename,filesize,files,update,bot,message,thread=None,jdb=None):
    try:
        err = None
        bot.editMessageText(message,'📡Conectando con el servidor ')
        evidence = None
        fileid = None
        user_info = jdb.get_user(update.message.sender.username)
        cloudtype = user_info['moodle_host']
        proxy = ProxyCloud.parse(user_info['proxy'])
        draftlist=[]
        if cloudtype != 'https:/u.cu/':
            host = user_info['moodle_host']
            user = user_info['moodle_user']
            passw = user_info['moodle_password']
            repoid = user_info['moodle_repo_id']
            token = moodlews.get_webservice_token(host,user,passw,proxy=proxy)
            if token == None:
                token = moodlews.get_webservice_token(host,user,passw,proxy=proxy)
                if token == None:
                    token = moodlews.get_webservice_token(host,user,passw,proxy=proxy)
            print(token)
            for file in files:
                    if cloudtype != 'https://evea.uh.cu/' or 'https://moodle.uclv.edu.cu/':
                        data = asyncio.run(moodlews.webservice_upload_file(host,token,file,progressfunc=uploadFile,proxy=proxy,args=(bot,message,filename,thread)))
                        while not moodlews.store_exist(file):pass
                        data = moodlews.get_store(file)
                        if data[0]:
                            urls = moodlews.make_draft_urls(data[0])
                            if cloudtype != 'https://moodle.uclv.edu.cu/':
                                draftlist.append({'file':file,'url':urls[0]})
                        else:
                            err = data[1]
                            print(err)
            else:
                print('No sirve:')
                host = user_info['moodle_host']
                user = user_info['moodle_user']
                passw = user_info['moodle_password']
                repoid = user_info['moodle_repo_id']
                cli = MoodleClient2(host,user,passw,repoid,proxy)
                for file in files:
                    data = asyncio.run(cli.LoginUpload(file, uploadFile, (bot, message, filename, thread)))
                    while cli.status is None: pass
                    data = cli.get_store(file)
                    if data:
                        if 'error' in data:
                            err = data['error']
                            print(err)
                        else:
                            draftlist.append({'file': file, 'url': data['url']})
        return draftlist,err
    except Exception as ex:
        bot.editMessageText(message,'Error:\n1-Compruebe que la nube esta activa\n2-Verifique su proxy\n3-Revise su cuenta')


def processFile(update,bot,message,file,thread=None,jdb=None):
    file_size = get_file_size(file)
    getUser = jdb.get_user(update.message.sender.username)
    max_file_size = 1024 * 1024 * getUser['zips']
    file_upload_count = 0
    client = None
    findex = 0
    if file_size > max_file_size:
        compresingInfo = infos.createCompresing(file,file_size,max_file_size)
        bot.editMessageText(message,compresingInfo)
        zipname = str(file).split('.')[0] + createID()
        mult_file = zipfile.MultiFile(zipname,max_file_size)
        zip = zipfile.ZipFile(mult_file,  mode='w', compression=zipfile.ZIP_DEFLATED)
        zip.write(file)
        zip.close()
        mult_file.close()
        name = file
        data,err = processUploadFiles(name,file_size,mult_file.files,update,bot,message,jdb=jdb)
        try:
            os.unlink(file)
        except:pass
        file_upload_count = len(zipfile.files)
    else:
        name = file
        data,err = processUploadFiles(name,file_size,[name],update,bot,message,jdb=jdb)
        file_upload_count = 1
    bot.editMessageText(message,'Preparando 📦...')
    bot.deleteMessage(message.chat.id,message.message_id)
    files = []
    if data:
        for draft in data:
            files.append({'name':draft['file'],'directurl':draft['url']})
    i=0
    while i < len(files):
        if i+1 < len(files):
            print('Mas de un link')
        i+=2
    filesInfo = infos.createFileMsg(file,files)
    bot.sendMessage(message.chat.id,filesInfo,parse_mode='html')
    if len(files) > 0:     
        txtname = str(file).split('/')[-1].split('.')[0] + '.txt'
        txtname = txtname.replace(' ','')
        sendTxt(txtname,files,update,bot)
    else:
        bot.sendMessage(update.message.chat.id,f'⚠️Error: 400 Bad Request')
      
def ddl(update,bot,message,url,file_name='',thread=None,jdb=None):
    downloader = Downloader()
    file = downloader.download_url(url,progressfunc=downloadFile,args=(bot,message,thread))
    if not downloader.stoping:
        if file:
            processFile(update,bot,message,file,jdb=jdb)

def sendTxt(name,files,update,bot):
                txt = open(name,'w')
                fi = 0
                for f in files:
                    separator = ''
                    if fi < len(files)-1:
                        separator += '\n'
                    txt.write(f['directurl']+separator)
                    fi += 1
                txt.close()
                bot.sendFile(update.message.chat.id,name)
                os.unlink(name)

def onmessage(update,bot:ObigramClient):
    try:
        thread = bot.this_thread
        username = update.message.sender.username
        #tl_admin_user = os.environ.get('tl_admin_user')

        #set in debug
        tl_admin_user = 'barberGeminis98'

        jdb = JsonDatabase('database')
        jdb.check_create()
        jdb.load()

        user_info = jdb.get_user(username)

        if username == tl_admin_user or user_info:  # validate user
            if user_info is None:
                if username == tl_admin_user:
                    jdb.create_admin(username)
                else:
                    jdb.create_user(username)
                user_info = jdb.get_user(username)
                jdb.save()
        else:
            mensaje = "No tienes acceso.\n👨🏻‍💻Dev: @XKorp00\n"
            intento_msg = "💢El usuario @"+username+ " ha intentado acceder al bot sin autorización💢"
            bot.sendMessage(update.message.chat.id,mensaje)
            bot.sendMessage(1456793817,intento_msg)
            return

        msgText = ''
        try: msgText = update.message.text
        except:pass

        # comandos de admin
        if '/add' in msgText:
            isadmin = jdb.is_admin(username)
            if isadmin:
                try:
                    user = str(msgText).split(' ')[1]
                    jdb.create_user(user)
                    jdb.save()
                    msg = '✅ @'+user+' ha sido autorizado a usar el bot!'
                    bot.sendMessage(update.message.chat.id,msg)
                except:
                    bot.sendMessage(update.message.chat.id,f'⚠️Comando inválido /add username')
            else:
                bot.sendMessage(update.message.chat.id,'👮No tienes permiso de administrador👮')
            return
            
        if '/ban' in msgText:
            isadmin = jdb.is_admin(username)
            if isadmin:
                try:
                    user = str(msgText).split(' ')[1]
                    if user == username:
                        bot.sendMessage(update.message.chat.id,'⚠️No te puedes banear a ti mismo⚠️')
                        return
                    jdb.remove(user)
                    jdb.save()
                    msg = 'El usuario @'+user+' ha sido baneado del bot!'
                    bot.sendMessage(update.message.chat.id,msg)
                except:
                    bot.sendMessage(update.message.chat.id,'⚠️Comando inválido /ban username⚠️')
            else:
                bot.sendMessage(update.message.chat.id,'👮No tienes permiso de administrador👮')
            return

        if '/db' in msgText:
            isadmin = jdb.is_admin(username)
            if isadmin:
                database = open('database.jdb','r')
                bot.sendMessage(update.message.chat.id,database.read())
                database.close()
            else:
                bot.sendMessage(update.message.chat.id,'👮No tienes permiso de administrador👮')
            return
        # end

        # comandos de usuario
        if '/help' in msgText:
            message = bot.sendMessage(update.message.chat.id,'📄Guía de Usuario:')
            tuto = open('tuto.txt','r')
            bot.sendMessage(update.message.chat.id,tuto.read())
            tuto.close()
            return
        if '/myuser' in msgText:
            getUser = user_info
            if getUser:
                statInfo = infos.createStat(username,getUser,jdb.is_admin(username))
                bot.sendMessage(update.message.chat.id,statInfo)
                return

        if '/zips' in msgText:
            getUser = user_info
            if getUser:
                try:
                   size = int(str(msgText).split(' ')[1])
                   getUser['zips'] = size
                   jdb.save_data_user(username,getUser)
                   jdb.save()
                   msg = '🗜️Ahora serán de '+ sizeof_fmt(size*1024*1024)+' las partes📚'
                   bot.sendMessage(update.message.chat.id,msg)
                except:
                   bot.sendMessage(update.message.chat.id,'⚠️Comando inválido /zips zips_size⚠️')    
                return

        if '/acc' in msgText:
            try:
                account = str(msgText).split(' ',2)[1].split(',')
                user = account[0]
                passw = account[1]
                getUser = user_info
                if getUser:
                    getUser['moodle_user'] = user
                    getUser['moodle_password'] = passw
                    jdb.save_data_user(username,getUser)
                    jdb.save()
                    statInfo = infos.createStat(username,getUser,jdb.is_admin(username))
                    bot.sendMessage(update.message.chat.id,statInfo)
            except:
                bot.sendMessage(update.message.chat.id,'⚠️Comando inválido /acc user,password⚠️')
            return

        if '/host' in msgText:
            try:
                cmd = str(msgText).split(' ',2)
                host = cmd[1]
                getUser = user_info
                if getUser:
                    getUser['moodle_host'] = host
                    jdb.save_data_user(username,getUser)
                    jdb.save()
                    statInfo = infos.createStat(username,getUser,jdb.is_admin(username))
                    bot.sendMessage(update.message.chat.id,statInfo)
            except:
                bot.sendMessage(update.message.chat.id,'⚠️Comando inválido /host cloud_url⚠️')
            return

        if '/repo' in msgText:
            try:
                cmd = str(msgText).split(' ',2)
                repoid = int(cmd[1])
                getUser = user_info
                if getUser:
                    getUser['moodle_repo_id'] = repoid
                    jdb.save_data_user(username,getUser)
                    jdb.save()
                    statInfo = infos.createStat(username,getUser,jdb.is_admin(username))
                    bot.sendMessage(update.message.chat.id,statInfo)
            except:
                bot.sendMessage(update.message.chat.id,'⚠️Comando inválido /repo moodle_repo_id⚠️')
            return

        if '/uptype' in msgText:
            try:
                cmd = str(msgText).split(' ',2)
                type = cmd[1]
                getUser = user_info
                if getUser:
                    getUser['uploadtype'] = type
                    jdb.save_data_user(username,getUser)
                    jdb.save()
                    statInfo = infos.createStat(username,getUser,jdb.is_admin(username))
                    bot.sendMessage(update.message.chat.id,statInfo)
            except:
                bot.sendMessage(update.message.chat.id,'⚠️Comando inválido /uptype (evidence,draft,blog,calendar)⚠️')
            return

        if '/proxy' in msgText:
            try:
                cmd = str(msgText).split(' ',2)
                proxy = cmd[1]
                getUser = user_info
                if getUser:
                    getUser['proxy'] = proxy
                    jdb.save_data_user(username,getUser)
                    jdb.save()
                    msg = '🧬Perfecto, proxy equipado correctamente.'
                    bot.sendMessage(update.message.chat.id,msg)
            except:
                if user_info:
                    user_info['proxy'] = ''
                    statInfo = infos.createStat(username,user_info,jdb.is_admin(username))
                    bot.sendMessage(update.message.chat.id,'🧬Error equipando el proxy.')
            return
                    
        if '/cancel_' in msgText:
            try:
                cmd = str(msgText).split('_',2)
                tid = cmd[1]
                tcancel = bot.threads[tid]
                msg = tcancel.getStore('msg')
                tcancel.store('stop',True)
                time.sleep(3)
                bot.editMessageText(msg,'🚫Tarea cancelada🚫')
            except Exception as ex:
                print(str(ex))
            return

        message = bot.sendMessage(update.message.chat.id,'🎐Analizando enlace...')

        thread.store('msg',message)

        if '/start' in msgText:
            start_msg = '╭───ⓘ🎐Hola @' + str(username)+'─〄\n│\n'
            start_msg+= '├🔗 Soporto links\n│\n'
            start_msg+= '├👨‍💻Dev: @XKorp00\n│\n'
            start_msg+= '╰ⓘDisfuta del bot─〄\n'
            bot.editMessageText(message,start_msg)

        elif '/token' in msgText:
            message2 = bot.editMessageText(message,'🤖Obteniendo token, por favor espera...')

            try:
                proxy = ProxyCloud.parse(user_info['proxy'])
                client = MoodleClient(user_info['moodle_user'],
                                      user_info['moodle_password'],
                                      user_info['moodle_host'],
                                      user_info['moodle_repo_id'],proxy=proxy)
                loged = client.login()
                if loged:
                    token = client.userdata
                    modif = token['token']
                    bot.editMessageText(message2,'🤖Tú token es: '+modif)
                    client.logout()
                else:
                    bot.editMessageText(message2,'⚠️La moodle '+client.path+' no tiene token⚠️')
            except Exception as ex:
                bot.editMessageText(message2,'⚠️La moodle '+client.path+' no tiene token o revisa tú cuenta⚠️')       
       
        elif '/delete' in msgText:
            enlace = msgText.split('/delete')[-1]
            proxy = ProxyCloud.parse(user_info['proxy'])
            client = MoodleClient(user_info['moodle_user'],
                                   user_info['moodle_password'],
                                   user_info['moodle_host'],
                                   user_info['moodle_repo_id'],
                                   proxy=proxy)
            loged= client.login()
            if loged:
                deleted = client.delete(enlace)
                bot.sendMessage(update.message.chat.id, "Archivo eliminado con éxito...")

        elif '/uclv' in msgText:
            getUser = user_info
            getUser['moodle_host'] = "https://moodle.uclv.edu.cu/"
            getUser['uploadtype'] =  "calendar"
            getUser['moodle_user'] = "---"
            getUser['moodle_password'] = "---"
            getUser['moodle_repo_id'] = 4
            getUser['zips'] = 399
            jdb.save_data_user(username,getUser)
            jdb.save()
            statInfo = infos.createStat(username,getUser,jdb.is_admin(username))
            bot.editMessageText(message,"✅Configuración de la Uclv establecida")

        elif '/evea' in msgText:
            getUser = user_info
            getUser['moodle_host'] = "https://evea.uh.cu/"
            getUser['uploadtype'] =  "calendar"
            getUser['moodle_user'] = "---"
            getUser['moodle_password'] = "---"
            getUser['moodle_repo_id'] = 4
            getUser['zips'] = 99
            jdb.save_data_user(username,getUser)
            jdb.save()
            statInfo = infos.createStat(username,getUser,jdb.is_admin(username))
            bot.editMessageText(message,"✅Configuración de la Evea establecida")
        # end

        elif 'http' in msgText:
            url = msgText
            ddl(update,bot,message,url,file_name='',thread=thread,jdb=jdb)
        else: 
            bot.editMessageText(message,'⚠️Error analizando⚠️')
    except Exception as ex:
           print(str(ex))
  
def main():
    #set in debug
    bot_token = '5763989477:AAFGfvbYBhvW3-8_2Pe0qHL4z-sgkiySWN0'
    
    bot = ObigramClient(bot_token)
    bot.onMessage(onmessage)
    bot.run()
    asyncio.run()

if __name__ == '__main__':
    try:
        main()
    except:
        main()
