# coding:utf-8

import sys
import io
import os
import time

sys.path.append(os.getcwd() + "/class/core")
import mw

app_debug = False
if mw.isAppleSystem():
    app_debug = True


# /usr/lib/systemd/system/mongod.service
# /var/lib/mongo

def getPluginName():
    return 'mongodb'


def getPluginDir():
    return mw.getPluginDir() + '/' + getPluginName()


def getServerDir():
    return mw.getServerDir() + '/' + getPluginName()


def getInitDFile():
    if app_debug:
        return '/tmp/' + getPluginName()
    return '/etc/init.d/' + getPluginName()


def getConf():
    path = getServerDir() + "/mongodb.conf"
    return path


def getConfTpl():
    path = getPluginDir() + "/config/mongodb.conf"
    return path


def getInitDTpl():
    path = getPluginDir() + "/init.d/" + getPluginName() + ".tpl"
    return path


def getArgs():
    args = sys.argv[2:]
    tmp = {}
    args_len = len(args)

    if args_len == 1:
        t = args[0].strip('{').strip('}')
        t = t.split(':')
        tmp[t[0]] = t[1]
    elif args_len > 1:
        for i in range(len(args)):
            t = args[i].split(':')
            tmp[t[0]] = t[1]

    return tmp


def status():
    data = mw.execShell(
        "ps -ef|grep mongod |grep -v grep | grep -v python | grep -v mdserver-web | awk '{print $2}'")

    if data[0] == '':
        return 'stop'
    return 'start'


def initDreplace():

    file_tpl = getInitDTpl()
    service_path = os.path.dirname(os.getcwd())

    initD_path = getServerDir() + '/init.d'
    if not os.path.exists(initD_path):
        os.mkdir(initD_path)
    file_bin = initD_path + '/' + getPluginName()

    logs_dir = getServerDir() + '/logs'
    if not os.path.exists(logs_dir):
        os.mkdir(logs_dir)

    data_dir = getServerDir() + '/data'
    if not os.path.exists(data_dir):
        os.mkdir(data_dir)

    # initd replace
    content = mw.readFile(file_tpl)
    content = content.replace('{$SERVER_PATH}', service_path)
    mw.writeFile(file_bin, content)
    mw.execShell('chmod +x ' + file_bin)

    # config replace
    conf_content = mw.readFile(getConfTpl())
    conf_content = conf_content.replace('{$SERVER_PATH}', service_path)
    mw.writeFile(getServerDir() + '/mongodb.conf', conf_content)

    # systemd
    systemDir = mw.systemdCfgDir()
    systemService = systemDir + '/mongodb.service'
    systemServiceTpl = getPluginDir() + '/init.d/mongodb.service.tpl'
    if os.path.exists(systemDir) and not os.path.exists(systemService):
        service_path = mw.getServerDir()
        se_content = mw.readFile(systemServiceTpl)
        se_content = se_content.replace('{$SERVER_PATH}', service_path)
        mw.writeFile(systemService, se_content)
        mw.execShell('systemctl daemon-reload')

    return file_bin


def mgOp(method):
    file = initDreplace()
    if mw.isAppleSystem():
        data = mw.execShell(file + ' ' + method)
        if data[1] == '':
            return 'ok'
        return data[1]

    data = mw.execShell('systemctl ' + method + ' ' + getPluginName())
    if data[1] == '':
        return 'ok'
    return 'fail'


def start():
    mw.execShell(
        'export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/www/server/lib/openssl11/lib')
    return mgOp('start')


def stop():
    return mgOp('stop')


def reload():
    return mgOp('reload')


def restart():
    if os.path.exists("/tmp/mongodb-27017.sock"):
        mw.execShell('rm -rf ' + "/tmp/mongodb-27017.sock")

    return mgOp('restart')


def runInfo():
    import pymongo
    client = pymongo.MongoClient(host='127.0.0.1', port=27017)
    db = client.admin
    serverStatus = db.command('serverStatus')

    listDbs = client.list_database_names()

    showDbList = []
    for x in range(len(listDbs)):
        mongd = client[listDbs[x]]
        stats = mongd.command({"dbstats": 1})
        showDbList.append(stats)
    # print(showDbList)
    # print(serverStatus)
    # for key, value in serverStatus.items():
    #     print(key, value)
    result = {}
    result["version"] = serverStatus['version']
    result["uptime"] = serverStatus['uptime']

    result['db_path'] = getServerDir() + "/data"

    result["connections"] = serverStatus['connections']['current']
    if 'catalogStats' in serverStatus:
        result["collections"] = serverStatus['catalogStats']['collections']

    result["dbs"] = showDbList
    return mw.getJson(result)


def initdStatus():
    if mw.isAppleSystem():
        return "Apple Computer does not support"

    shell_cmd = 'systemctl status mongodb | grep loaded | grep "enabled;"'
    data = mw.execShell(shell_cmd)
    if data[0] == '':
        return 'fail'
    return 'ok'


def initdInstall():
    if mw.isAppleSystem():
        return "Apple Computer does not support"

    mw.execShell('systemctl enable mongodb')
    return 'ok'


def initdUinstall():
    if mw.isAppleSystem():
        return "Apple Computer does not support"

    mw.execShell('systemctl disable mongodb')
    return 'ok'


def runLog():
    f = getServerDir() + '/logs/mongodb.log'
    if os.path.exists(f):
        return f
    return getServerDir() + '/logs.pl'


def installPreInspection(version):
    if mw.isAppleSystem():
        return 'ok'

    sys = mw.execShell(
        "cat /etc/*-release | grep PRETTY_NAME |awk -F = '{print $2}' | awk -F '\"' '{print $2}'| awk '{print $1}'")

    if sys[1] != '':
        return '暂时不支持该系统'

    sys_id = mw.execShell(
        "cat /etc/*-release | grep VERSION_ID | awk -F = '{print $2}' | awk -F '\"' '{print $2}'")

    sysName = sys[0].strip().lower()
    sysId = sys_id[0].strip()

    supportOs = ['centos', 'ubuntu', 'debian', 'opensuse']
    if not sysName in supportOs:
        return '暂时仅支持{}'.format(','.join(supportOs))
    return 'ok'

if __name__ == "__main__":
    func = sys.argv[1]

    version = "4.4"
    if (len(sys.argv) > 2):
        version = sys.argv[2]

    if func == 'status':
        print(status())
    elif func == 'start':
        print(start())
    elif func == 'stop':
        print(stop())
    elif func == 'restart':
        print(restart())
    elif func == 'reload':
        print(reload())
    elif func == 'install_pre_inspection':
        print(installPreInspection(version))
    elif func == 'initd_status':
        print(initdStatus())
    elif func == 'initd_install':
        print(initdInstall())
    elif func == 'initd_uninstall':
        print(initdUinstall())
    elif func == 'run_info':
        print(runInfo())
    elif func == 'conf':
        print(getConf())
    elif func == 'run_log':
        print(runLog())
    else:
        print('error')
