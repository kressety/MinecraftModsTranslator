from json import dump, load
from os import chdir, getcwd, mkdir, walk
from os.path import dirname, exists, join, basename
from shutil import rmtree
from zipfile import ZipFile, is_zipfile

from PyQt6.QtWidgets import QWidget, QFileDialog

from UI.MainWindow import Ui_MainWindow
from functions.translationRequest import transJson, authPost


class jarTranslation(Ui_MainWindow, QWidget):
    def __init__(self, MainWindow):
        super().__init__()
        super().setupUi(MainWindow)
        self.Next.clicked.connect(self.onClickNext)
        self.Finish.clicked.connect(self.onClickFinish)
        self.ImportJar.clicked.connect(self.selectFile)
        self.isRestarted = None
        self.fileName = None
        self.workDir = None
        self.unzipDir = None
        self.originWork = '/en_us.json'
        self.oldWork = '/zh_cn.json'
        self.hasOldWork = False
        self.exportWork = getcwd() + '/export.json'
        self.authToken = None
        self.items = None
        self.transJson = None
        self.transList = None
        self.checkedJson = {}

    def isJar(self):
        if is_zipfile(self.workDir + self.fileName):
            self.addStatus('文件验证成功，准备解压')
            return True
        self.addStatus('文件验证失败，检查是否损坏')
        return False

    def unzipJar(self):
        chdir(self.workDir)
        unzipFile = ZipFile(self.fileName)
        if exists(self.unzipDir):
            rmtree(self.unzipDir)
        mkdir(self.unzipDir)
        unzipFile.extractall(self.unzipDir)
        unzipFile.close()
        self.addStatus('解压完成')

    def isTranslatable(self):
        for root, _, files in walk(self.unzipDir):
            if self.originWork[1:] in files:
                self.originWork = root + self.originWork
                if not self.isRestarted:
                    if self.oldWork[1:] in files:
                        self.oldWork = root + self.oldWork
                        self.hasOldWork = True
                        self.addStatus('已找到\'zh_cn.json\'文件')
                self.addStatus('已找到\'en_us.json\'文件')
                return True
        self.addStatus('未找到可翻译文件')
        return False

    def exec(self):
        originFile = open(self.originWork, 'r', encoding='UTF-8')
        originJson = load(originFile)
        originFile.close()
        if self.hasOldWork:
            oldFile = open(self.oldWork, 'r', encoding='UTF-8')
            oldJson = load(oldFile)
            oldFile.close()
            preparedJson = {}
            for i in originJson:
                if i not in oldJson:
                    preparedJson[i] = originJson[i]
            self.items = len(preparedJson)
            if self.items == 0:
                self.addStatus('没有可供翻译的条目')
                return
            exportFile = open(self.exportWork, 'w', encoding='UTF-8')
            self.transJson = transJson(self, preparedJson, self.authToken)
            dump(self.transJson, exportFile, indent=4)
            exportFile.close()
        else:
            self.items = len(originJson)
            if self.items == 0:
                self.addStatus('没有可供翻译的条目')
                return
            exportFile = open(self.exportWork, 'w', encoding='UTF-8')
            self.transJson = transJson(self, originJson, self.authToken)
            dump(self.transJson, exportFile, indent=4)
            exportFile.close()
        self.addStatus('共 {} 条需要翻译'.format(self.items))
        self.Next.setEnabled(True)
        self.transList = list(self.transJson.items())
        self.onClickNext()

    def nextItem(self):
        self.items -= 1
        return self.transList.pop(0)

    def receiveChecked(self, checked):
        self.checkedJson[checked[0]] = checked[1]

    def merge(self):
        if self.hasOldWork:
            oldFile = open(self.oldWork, 'r', encoding='UTF-8')
            oldJson = load(oldFile)
            oldFile.close()
            for key in self.checkedJson:
                oldJson[key] = self.checkedJson[key]
            newFile = open(self.oldWork, 'w', encoding='UTF-8')
            dump(oldJson, newFile, indent=4)
            newFile.close()
        else:
            transFile = open(dirname(self.originWork) + '/zh_cn.json', 'w', encoding='UTF-8')
            dump(self.checkedJson, transFile, indent=4)
            transFile.close()
        finishedArchive = ZipFile('zh_' + self.fileName, 'w')
        for root, _, files in walk(self.unzipDir):
            relaPath = root.replace(self.unzipDir, '')
            for file in files:
                finishedArchive.write(join(root, file), join(relaPath, file))
        finishedArchive.close()
        self.addStatus('合并完成')

    def getIsRestart(self):
        return self.isRestart.isChecked()

    def addStatus(self, text):
        self.Status.append(text + '\n')

    def setTag(self, text):
        self.Tag.setText(text)

    def getTag(self):
        return self.Tag.toPlainText()

    def setOrigin(self, text):
        self.Origin.setText(text)

    def setTranslated(self, text):
        self.Translated.setPlainText(text)

    def getTranslated(self):
        return self.Translated.toPlainText()

    def setUnchecked(self, number):
        self.Unchecked.setText('还剩 {} 个未校对'.format(number))

    def onClickNext(self):
        if self.getTag():
            self.receiveChecked([self.getTag(), self.getTranslated()])
        if self.items == 0:
            self.addStatus('已经全部校对，点击完成来合并文件')
            self.Next.setDisabled(True)
            self.Finish.setEnabled(True)
        else:
            item = self.nextItem()
            self.setTag(item[0])
            self.setOrigin(item[1]['src'])
            self.setTranslated(item[1]['dst'])
            self.setUnchecked(self.items)

    def onClickFinish(self):
        self.Finish.setDisabled(True)
        self.merge()

    def selectFile(self):
        self.ImportJar.setDisabled(True)
        path, _ = QFileDialog.getOpenFileName(self, '打开Jar文件', getcwd(), 'Jar File (*)')
        if path:
            self.fileName = basename(path)
            self.workDir = dirname(path)
            self.isRestarted = self.getIsRestart()
            self.unzipDir = '/uz_' + self.fileName[: -4]
            if exists('config.json'):
                try:
                    configFile = open('config.json', 'r', encoding='UTF-8')
                    configJson = load(configFile)
                    self.authToken = authPost(self, configJson)
                    configFile.close()
                except (TypeError, KeyError):
                    self.addStatus('config文件不符合规范')
                    return
            else:
                self.addStatus('config文件不存在，已重新创建，请填写后重新打开应用')
                configFile = open('config.json', 'w', encoding='UTF-8')
                configJson = {
                    'client_id': 'Enter your API Key',
                    'client_secret': 'Enter your Secret Key'
                }
                dump(configJson, configFile, indent=4)
                configFile.close()
                return
            if self.isJar():
                self.unzipJar()
            if self.isTranslatable():
                self.exec()
        else:
            self.ImportJar.setEnabled(True)
