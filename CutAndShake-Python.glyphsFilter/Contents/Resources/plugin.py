# encoding: utf-8

###########################################################################################################
#
#
#	Filter with dialog Plugin
#
#	Read the docs:
#	https://github.com/schriftgestalt/GlyphsSDK/tree/Glyphs4/Python%20Templates/Filter
#
#	For help on the use of Interface Builder:
#	https://github.com/schriftgestalt/GlyphsSDK/tree/Glyphs4/Python%20Templates
#
#
###########################################################################################################

from __future__ import division, print_function, unicode_literals

from random import random, randint

import objc
from Cocoa import NSAffineTransform, NSPoint
from GlyphsApp import Glyphs
from GlyphsApp.plugins import FilterWithDialog

CUTS_KEY = "com.mekkablue.CutAndShake.numberOfCuts"
MOVE_KEY = "com.mekkablue.CutAndShake.maxMove"
ROTATE_KEY = "com.mekkablue.CutAndShake.maxRotate"


class CutAndShake(FilterWithDialog):
	goodMeasure = 5.0

	# Definitions of IBOutlets
	dialog = objc.IBOutlet()
	numberOfCutsField = objc.IBOutlet()
	maxMoveField = objc.IBOutlet()
	maxRotateField = objc.IBOutlet()

	@objc.python_method
	def settings(self):
		self.menuName = Glyphs.localize({
			'en': 'Cut and Shake',
			'de': 'Schneiden und schütteln',
			'fr': 'Couper et secouer',
			'es': 'Cortar y agitar',
			'zh': '🤺碎片化',
		})

		self.actionButtonLabel = Glyphs.localize({
			'en': 'Apply',
			'de': 'Anwenden',
			'fr': 'Appliquer',
			'es': 'Aplicar',
			'zh': '应用',
		})

		# Load dialog from .nib (without .extension)
		self.loadNib('IBdialog', __file__)

	# On dialog show
	@objc.python_method
	def start(self):

		# Default settings
		Glyphs.registerDefaults({
			CUTS_KEY: 5,
			MOVE_KEY: 50.0,
			ROTATE_KEY: 20.0,
		})

		# Set value of text fields. setStringValue_() insists on a string,
		# and Glyphs.defaults hands out NSNumbers.
		self.numberOfCutsField.setStringValue_("%i" % self.cutsValue())
		self.maxMoveField.setStringValue_("%g" % self.moveValue())
		self.maxRotateField.setStringValue_("%g" % self.rotateValue())

		# Set focus to text field
		self.numberOfCutsField.becomeFirstResponder()

	# Action triggered by UI
	@objc.IBAction
	def setNumberOfCuts_(self, sender):
		Glyphs.defaults[CUTS_KEY] = sender.intValue()
		self.update()

	@objc.IBAction
	def setMaxMove_(self, sender):
		Glyphs.defaults[MOVE_KEY] = sender.floatValue()
		self.update()

	@objc.IBAction
	def setMaxRotate_(self, sender):
		Glyphs.defaults[ROTATE_KEY] = sender.floatValue()
		self.update()

	@objc.python_method
	def cutsValue(self):
		return int(Glyphs.defaults[CUTS_KEY] or 2)

	@objc.python_method
	def moveValue(self):
		return float(Glyphs.defaults[MOVE_KEY] or 10)

	@objc.python_method
	def rotateValue(self):
		return float(Glyphs.defaults[ROTATE_KEY] or 5)

	# Actual filter
	@objc.python_method
	def filter(self, layer, inEditView, customParameters):
		# Called through UI, use stored value
		numberOfCuts = self.cutsValue()
		maxMove = self.moveValue()
		maxRotate = self.rotateValue()

		# Called on font export, overwrite with values from customParameters:
		if 'cuts' in customParameters:
			numberOfCuts = int(customParameters['cuts'] or 2)
		if 'move' in customParameters:
			maxMove = abs(float(customParameters['move'] or 10))
		if 'rotate' in customParameters:
			maxRotate = abs(float(customParameters['rotate'] or 5))

		# process the layer:
		self.randomCutLayer(layer, numberOfCuts)
		self.randomMovePaths(layer, maxMove)
		self.randomRotatePaths(layer, maxRotate)

	@objc.python_method
	def generateCustomParameter(self):
		return "%s; cuts:%i; move:%g; rotate:%g" % (
			self.__class__.__name__,
			self.cutsValue(),
			self.moveValue(),
			self.rotateValue(),
		)

	@objc.python_method
	def randomCutLayer(self, thisLayer, numberOfCuts):
		if not thisLayer.paths:
			return
		bounds = thisLayer.bounds
		lowestY = bounds.origin.y - self.goodMeasure
		highestY = bounds.origin.y + bounds.size.height + self.goodMeasure
		leftmostX = bounds.origin.x - self.goodMeasure
		rightmostX = bounds.origin.x + bounds.size.width + self.goodMeasure
		for _ in range(numberOfCuts):
			# make either horizontal or vertical cut:
			if randint(0, 1) == 0:
				point1 = NSPoint(leftmostX, self.somewhereBetween(lowestY, highestY))
				point2 = NSPoint(rightmostX, self.somewhereBetween(lowestY, highestY))
			else:
				point1 = NSPoint(self.somewhereBetween(leftmostX, rightmostX), lowestY)
				point2 = NSPoint(self.somewhereBetween(leftmostX, rightmostX), highestY)
			thisLayer.cutBetweenPoints(point1, point2)

	@objc.python_method
	def randomMovePaths(self, thisLayer, maximumMove):
		halfRange = maximumMove / (2 ** 0.5)
		for thisPath in thisLayer.paths:
			xMove = self.somewhereBetween(-halfRange, halfRange)
			yMove = self.somewhereBetween(-halfRange, halfRange)
			shift = NSAffineTransform.transform()
			shift.translateXBy_yBy_(xMove, yMove)
			thisPath.applyTransform(shift.transformStruct())

	@objc.python_method
	def somewhereBetween(self, minimum, maximum):
		minMaxRange = maximum - minimum
		randomFloat = minimum + random() * minMaxRange
		return randomFloat

	@objc.python_method
	def randomRotatePaths(self, thisLayer, maximumRotate):
		for thisPath in thisLayer.paths:
			bounds = thisPath.bounds
			centerX = bounds.origin.x + bounds.size.width / 2.0
			centerY = bounds.origin.y + bounds.size.height / 2.0
			degrees = self.somewhereBetween(-maximumRotate, maximumRotate)
			rotation = NSAffineTransform.transform()
			rotation.translateXBy_yBy_(centerX, centerY)
			rotation.rotateByDegrees_(degrees)
			rotation.translateXBy_yBy_(-centerX, -centerY)
			thisPath.applyTransform(rotation.transformStruct())

	@objc.python_method
	def __file__(self):
		"""Please leave this method unchanged"""
		return __file__
