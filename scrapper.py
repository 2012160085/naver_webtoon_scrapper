from urllib.request import Request
from urllib.request import urlopen
from urllib.request import urlretrieve
import time
import pickle
import re
import requests
from bs4 import BeautifulSoup
import random
import threading
import os
import numpy as np
import urllib.request
from multiprocessing import Process, Queue, Pool
header = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.108 Safari/537.36'}





def GatherDuty(inque,outque,cname):
	
	while True:
		try:
			book = inque.get_nowait()
		except:
			break
		else:
			taskListFromId(outque,book[0],book[1],cname)
def taskListFromId(que,id_,prog,cname):
	ss = requests.Session()
	listbs = PageBsobj(ss,'http://comic.naver.com/webtoon/list.nhn?titleId='+id_,header)
	maxno = GetMaxNo(id_)
	no_ = int(prog)
	if maxno is not None:
		if no_ != maxno:
			if no_+1 != maxno:
				print( '업데이트 필요 : [%4s화~%4s화] [%s]' % (str(no_+1),str(maxno),cname[id_]))
			else:
				print( '업데이트 필요 : [%7s화] [%s]' % (str(maxno),cname[id_]))
			que.put([id_,str(no_+1),str(maxno+1)])
		else:
			print('업데이트 항목 없음 :',cname[id_])

def GetUrls(inque,outque,flagque):
	ss = requests.Session()
	while True:
		try:
			iq = inque.get_nowait()
		except:
			print('URL 가져오기 중지 됨')
			break
		else:
			id_ = iq[0]
			for int_no_ in range(int(iq[1]),int(iq[2])):
				no_ = str(int_no_)
				while True:
					if outque.qsize() < 2000:
						try:
							listbs = PageBsobj(ss,'http://comic.naver.com/webtoon/detail.nhn?titleId='+id_+'&no='+no_,header)
							state = isValid(listbs,no_)
							if state  == 'good':
								i = 0
								imglinks = listbs.find('div',{'class':'wt_viewer'}).findAll('img')
								lng = len(imglinks)
								for imglink in imglinks:
									if i + 1 == lng:
										outque.put([id_,no_,i,imglink.attrs['src'],True])
									else:
										outque.put([id_,no_,i,imglink.attrs['src'],False])
									i = i + 1
								
							elif state == 'log':
								print('로그인 요구 페이지 :','http://comic.naver.com/webtoon/detail.nhn?titleId='+id_+'&no='+no_)
								flagque.put([id_,no_])
							elif state == 'dup':
								print('사라진 페이지 리다이렉트 :','http://comic.naver.com/webtoon/detail.nhn?titleId='+id_+'&no='+no_)
								flagque.put([id_,no_])
							elif state == 'oz':
								flagque.put([id_,no_])
								print('oz뷰어 사용','http://comic.naver.com/webtoon/detail.nhn?titleId='+id_+'&no='+no_)
							else:
								print('알수없는오류 발생')
						except:
							print('이미지 링크 가져오는 중 오류 발생..')
							time.sleep(random.random()+0.1)
						else:
							
							break
					else:
						s0 = outque.qsize()
						time.sleep(20)
						s1 = outque.qsize()
						ups = int((s1-s0)/20)
						print(ups, 'URL / SEC')
				
def isValid(bs,no):
	try:
		validUrl = bs.find('div',{'class':'thumb'}).find('a').attrs['href']
		if bs.find('div',{'class':'oz-pages'}) is not None:

			return 'oz'
		a= re.compile('no=[0-9]*')
		if a.search(validUrl).group()[3:] == no:
			return 'good'
		else:
			
			return 'dup'
	except:
		if bs.find('div',{'class':'find_info'}) is not None:
			
			return 'log'
		else:
			
			return 'unknown'
def PageBsobj(ses,url,head):
	page_response = ses.get(url,headers = head)
	return BeautifulSoup(page_response.text,'html.parser')

def FindWtId(lib,cname,que):
	ss = requests.Session()
	bs = PageBsobj(ss,'http://comic.naver.com/webtoon/weekday.nhn',header)
	have = []
	for link in bs.findAll('a',{'href':re.compile(".*/webtoon/list\.nhn\?titleId=.*"),'class':'title'}):
		if link.get_text() not in have:
			have.append(link.get_text())
			cid = re.compile('Id=[0-9]*').search(link.attrs['href']).group()[3:]
			cname[cid] = folder_usable(link.get_text())
			if cid not in lib:
				que.put([cid,'0'])
				lib[cid] = '0'
				
			else:
				que.put([cid,lib[cid]])
def folder_usable(st):
	nn = ""
	for ii in st:
		if ii not in '.\/:*?"<>|':
			nn += ii
		if ii == '?':
			nn += '¿'
	return nn

def GetMaxNo(id_):
	
	ret = 1
	while True:
		try:
			ss = requests.Session()
			listbs = PageBsobj(ss,'http://comic.naver.com/webtoon/list.nhn?titleId='+id_,header)
			nono = listbs.find('td',{'class':'title'}).find('a').attrs['href']
			return int(re.compile('no=[0-9]*').search(nono).group()[3:])
		except:
			print(id_,'최신화 정보 가져오는 중 오류... 재시도:',ret)
			time.sleep(random.random()+0.1)
			if( ret > 20):
				return None
			ret += 1
			

	

def DownloadFromUrl(inque,outque,cname):
	while True:
		try:
			inp = inque.get()
		except:
			print('url 큐가 비었음')
			break
		else:
			id_ = inp[0]
			no_ = inp[1]
			i = inp[2]
			url = inp[3]
			flag = inp[4]
			header['referer'] = 'http://comic.naver.com/webtoon/detail.nhn?titleId='+id_+'&no='+no_
			ses = requests.session()
			r = ses.get(url,headers = header)
			dir = os.getcwd() + "/navercomic/" + cname[id_] + "/"
			if not os.path.isdir(dir):
				os.makedirs(dir)
			if r.status_code == 200:
				
				
				with open(dir+ no_ + '_' + str(i)+'.jpg', 'wb') as f:
					for chunk in r.iter_content():
						f.write(chunk)
				print('저장완료;', dir+ no_+'_'+str(i))
				if flag:
					
					outque.put([id_,str(int(no_))])
def save_obj(obj, name ):
	dir = os.getcwd()+"/navercomic/"
	if not os.path.isfile(dir):
		os.makedirs(dir)
	with open(name + '.pkl', 'wb') as f:
		pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)
def load_obj(name ):
    with open(name + '.pkl', 'rb') as f:
        return pickle.load(f)
def folder_usable(st):
	nn = ""
	for ii in st:
		if ii not in '.\/:*?"<>|':
			nn += ii
		if ii == '?':
			nn += '¿'
	return nn
def saver(lib,inque):
	lib_cop = lib.copy()
	stack = 0
	while True:
		try:
			dt = inque.get_nowait()
			stack = stack + 1
		except:
			
			save_obj(lib_cop,'tw_lib')
			time.sleep(3)
			print('saver 중지 됨')
		else:
			lib_cop[dt[0]] = dt[1]
			if stack > 10:
				stack = 0
				save_obj(lib_cop,'tw_lib')
def save_obj(obj, name ):
	with open(os.getcwd()+'/navercomic/' +name + '.pkl', 'wb') as f:
		pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)
def load_obj(name ):
	mydir = os.getcwd()
	with open(mydir+'/navercomic/' + name + '.pkl', 'rb') as f:
		return pickle.load(f)			
def check():

	dir = os.getcwd()+"/navercomic/"
	if not os.path.isdir(dir):
		os.makedirs(dir)
	for fname in ['tw_lib.pkl']:
		dir = os.getcwd()+'/navercomic/' + fname
		if not os.path.isfile(dir):
			ssf = open(dir, 'wb')
			pickle.dump({}, ssf, pickle.HIGHEST_PROTOCOL)
			ssf.close()
if __name__ == '__main__':
	check()
	print('<<<<<<<<<<<<<<<<<<<업데이트 목록 수집>>>>>>>>>>>>>>>>>>>>>>>>>')
	id_q = Queue()
	url_q = Queue()
	down_q = Queue()
	data_q = Queue()

	libr = {}
	libr = load_obj('tw_lib')
	libr_name= {}
	FindWtId(libr,libr_name,id_q)

	gatherProcess = []
	for i in range(4):
		proc_g = Process(target=GatherDuty, args = (id_q,url_q,libr_name))
		gatherProcess.append(proc_g)
		proc_g.start()
	for proc in gatherProcess:
		time.sleep(0.1)
		proc.join()
	print('<<<<<<<<<<<<<<<<<<<업데이트 목록 수집 완료 >>>>>>>>>>>>>>>>>>>>>>>>>')
	
	workProcess = []
	for i in range(4):
		proc_g = Process(target=DownloadFromUrl, args = (down_q,data_q,libr_name))
		workProcess.append(proc_g)
		proc_g.start()
	proc_geturl = Process(target=GetUrls, args = (url_q,down_q,data_q))
	workProcess.append(proc_geturl)
	proc_geturl.start()
	
	proc_save = Process(target=saver, args = (libr,data_q))
	workProcess.append(proc_save)
	proc_save.start()
	for proc in workProcess:
		proc.join()
	
