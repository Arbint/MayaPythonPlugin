import maya.cmds as mc
import maya.mel as mel
from maya.OpenMaya import MVector
import maya.OpenMayaUI as omui
from PySide2.QtWidgets import QVBoxLayout, QWidget, QPushButton, QMainWindow, QHBoxLayout, QGridLayout, QLineEdit, QLabel, QSlider
from PySide2.QtCore import Qt
from shiboken2 import wrapInstance

class LimbRiggerWidget(QWidget):
    def __init__(self):
        mainWindow: QMainWindow = LimbRiggerWidget.GetMayaMainWindow()

        for existing in mainWindow.findChildren(QWidget, LimbRiggerWidget.GetWindowUniqueId()):
            existing.deleteLater()

        super().__init__(parent=mainWindow)

        self.setWindowTitle("Limb Rigging Tool")
        self.setWindowFlags(Qt.Window)
        self.setObjectName(LimbRiggerWidget.GetWindowUniqueId())
        self.controllerSize = 15

        self.masterLayout = QVBoxLayout()
        self.setLayout(self.masterLayout)

        hintLabel = QLabel("Please Select the Root, middle, and end joint of your Limb:")
        self.masterLayout.addWidget(hintLabel)

        controllerSizeCtrlLayout = QHBoxLayout()
        self.masterLayout.addLayout(controllerSizeCtrlLayout)

        controllerSizeCtrlLayout.addWidget(QLabel("Controller Size: "))
        controllerSizeSlider = QSlider()
        controllerSizeSlider.setValue(self.controllerSize)
        controllerSizeSlider.setMinimum(1)
        controllerSizeSlider.setMaximum(30)
        controllerSizeSlider.setOrientation(Qt.Horizontal)
        controllerSizeCtrlLayout.addWidget(controllerSizeSlider)
        self.sizeDisplayLabel = QLabel(str(self.controllerSize))
        controllerSizeSlider.valueChanged.connect(self.ControllerSizeChanged)
        controllerSizeCtrlLayout.addWidget(self.sizeDisplayLabel)

        rigLimbBtn = QPushButton("Rig the Limb")
        rigLimbBtn.clicked.connect(self.RigTheLimb)
        self.masterLayout.addWidget(rigLimbBtn)

    def RigTheLimb(self):
        selection = mc.ls(sl=True)

        rootJnt = selection[0]
        midJnt = selection[1]
        endJnt = selection[2]

        rootFKCtrl, rootFKCtrlGrp = self.CreateFKForJnt(rootJnt) 
        midFKCtrl, midFKCtrlGrp = self.CreateFKForJnt(midJnt)
        endFKCtrl, endFKCtrlGrp = self.CreateFKForJnt(endJnt)

        mc.parent(midFKCtrlGrp, rootFKCtrl)
        mc.parent(endFKCtrlGrp, midFKCtrl)

        ikEndCtrlName, ikEndCtrlGrpName, midIkCtrlName, midIkCtrlGrpName, ikHandleName = self.CreateIkControl(rootJnt, midJnt, endJnt)

        ikfkBlendCtrlName = "ac_ikfk_blend_" + rootJnt
        mel.eval(f"curve -d 1 -n {ikfkBlendCtrlName} -p -3 1 0 -p -1 1 0 -p -1 3 0 -p 1 3 0 -p 1 1 0 -p 3 1 0 -p 3 -1 0 -p 1 -1 0 -p 1 -3 0 -p -1 -3 0 -p -1 -1 0 -p -3 -1 0 -p -3 1 0 -k 0 -k 1 -k 2 -k 3 -k 4 -k 5 -k 6 -k 7 -k 8 -k 9 -k 10 -k 11 -k 12 ;")
        ikfkBlendCtrlGrpName = ikfkBlendCtrlName + "_grp"
        mc.group(ikfkBlendCtrlName, n = ikfkBlendCtrlGrpName)

        rootJntPosVals = mc.xform(rootJnt, t=True, q=True, ws=True)
        rootJntPos = MVector(rootJntPosVals[0], rootJntPosVals[1], rootJntPosVals[2])
        ikfkBlendCtrlPos = rootJntPos + MVector(rootJntPos.x, 0, 0)
        mc.move(ikfkBlendCtrlPos[0], ikfkBlendCtrlPos[1], ikfkBlendCtrlPos[2], ikfkBlendCtrlGrpName)

        ikfkBlendAttrName = "ikfk_blend"
        mc.addAttr(ikfkBlendCtrlName, ln=ikfkBlendAttrName, k=True, min = 0, max = 1)

        mc.expression(s=f"{rootFKCtrlGrp}.v=1-{ikfkBlendCtrlName}.{ikfkBlendAttrName};")
        mc.expression(s=f"{ikEndCtrlGrpName}.v={ikfkBlendCtrlName}.{ikfkBlendAttrName};")
        mc.expression(s=f"{midIkCtrlGrpName}.v={ikfkBlendCtrlName}.{ikfkBlendAttrName};")
        mc.expression(s=f"{ikHandleName}.ikBlend={ikfkBlendCtrlName}.{ikfkBlendAttrName};")

        endJntOrientConstraint = mc.listConnections(endJnt, s=True, t="orientConstraint")[0]
        mc.expression(s=f"{endJntOrientConstraint}.{endFKCtrl}W0=1-{ikfkBlendCtrlName}.{ikfkBlendAttrName};")
        mc.expression(s=f"{endJntOrientConstraint}.{ikEndCtrlName}W1={ikfkBlendCtrlName}.{ikfkBlendAttrName};")

        topGrpName = f"{rootJnt}_rig_grp"

        mc.group([rootFKCtrlGrp, ikEndCtrlGrpName, midIkCtrlGrpName, ikfkBlendCtrlGrpName], n = topGrpName)

    def CreateFKForJnt(self, jnt):
        fkCtrlName = "ac_fk_" + jnt
        fkCtrlGrpName = fkCtrlName + "_grp"
        mc.circle(n=fkCtrlName, r=self.controllerSize, nr=(1,0,0))
        mc.group(fkCtrlName, n = fkCtrlGrpName)
        mc.matchTransform(fkCtrlGrpName, jnt)
        mc.orientConstraint(fkCtrlName, jnt)
        return fkCtrlName, fkCtrlGrpName
        
    def CreateIkControl(self, rootJnt, midJnt, endJnt):
        # wrist controller
        ikEndCtrlName = "ac_ik_" + endJnt
        mel.eval(f"curve -d 1 -n {ikEndCtrlName} -p -0.5 0.5 0.5 -p 0.5 0.5 0.5 -p 0.5 -0.5 0.5 -p -0.5 -0.5 0.5 -p -0.5 0.5 0.5 -p -0.5 0.5 -0.5 -p -0.5 -0.5 -0.5 -p -0.5 -0.5 0.5 -p -0.5 -0.5 -0.5 -p 0.5 -0.5 -0.5 -p 0.5 -0.5 0.5 -p 0.5 -0.5 -0.5 -p 0.5 0.5 -0.5 -p 0.5 0.5 0.5 -p 0.5 0.5 -0.5 -p -0.5 0.5 -0.5 -k 0 -k 1 -k 2 -k 3 -k 4 -k 5 -k 6 -k 7 -k 8 -k 9 -k 10 -k 11 -k 12 -k 13 -k 14 -k 15 ;")
        mc.scale(self.controllerSize, self.controllerSize, self.controllerSize, ikEndCtrlName, r=True)
        mc.makeIdentity(ikEndCtrlName, apply=True) # freeze transformation
        ikEndCtrlGrpName = ikEndCtrlName + "_grp"
        mc.group(ikEndCtrlName, n = ikEndCtrlGrpName)
        mc.matchTransform(ikEndCtrlGrpName, endJnt)
        mc.orientConstraint(ikEndCtrlName, endJnt)

        # ik handle
        ikHandleName = "ikHandle_" + endJnt
        mc.ikHandle(n=ikHandleName, sj=rootJnt, ee=endJnt, sol="ikRPsolver")

        rootJntPosVals = mc.xform(rootJnt, q=True, t=True, ws=True) # getting the world space(ws=True) translate (t=True) of the root Jnt, as a list of 3 values
        rootJntPos = MVector(rootJntPosVals[0], rootJntPosVals[1], rootJntPosVals[2])

        endJntPosVals = mc.xform(endJnt, q=True, t=True, ws=True)
        endJntPos = MVector(endJntPosVals[0], endJntPosVals[1], endJntPosVals[2])

        poleVectorVals = mc.getAttr(ikHandleName + ".poleVector")[0]
        poleVector = MVector(poleVectorVals[0], poleVectorVals[1], poleVectorVals[2])
        poleVector.normalize()

        vectorToEnd = endJntPos - rootJntPos
        limbDirOffset: MVector = vectorToEnd/2

        poleVectorDirOffset = poleVector * limbDirOffset.length()
        midIkCtrlPos: MVector = rootJntPos + limbDirOffset + poleVectorDirOffset

        midIkCtrlName = "ac_ik_" + midJnt
        mc.spaceLocator(n=midIkCtrlName)

        midIkCtrlGrpName = midIkCtrlName + "_grp"
        mc.group(midIkCtrlName, n = midIkCtrlGrpName)
        mc.move(midIkCtrlPos.x,midIkCtrlPos.y, midIkCtrlPos.z, midIkCtrlGrpName)

        mc.parent(ikHandleName, ikEndCtrlName)
        mc.poleVectorConstraint(midIkCtrlName, ikHandleName)
        mc.setAttr(ikHandleName+".v", 0)

        return ikEndCtrlName, ikEndCtrlGrpName, midIkCtrlName, midIkCtrlGrpName, ikHandleName

    def ControllerSizeChanged(self, sliderVal):
        self.sizeDisplayLabel.setText(str(sliderVal))
        self.controllerSize = sliderVal

    @staticmethod
    def GetMayaMainWindow():
        mainWindow = omui.MQtUtil.mainWindow()
        return wrapInstance(int(mainWindow), QMainWindow)

    @staticmethod
    def GetWindowUniqueId():
        return "6cd981868a7e96b8a673fa9c1f1649c3"

def Run():
    LimbRiggerWidget().show()

