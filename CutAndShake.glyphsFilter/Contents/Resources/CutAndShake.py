#!/usr/bin/env python
# encoding: utf-8

import objc
from Foundation import *
from AppKit import *
import sys, os, re
import random
import math

class GlyphsFilterCutAndShake ( GSFilterPlugin ):
	goodMeasure = 5.0
	
	_numberOfCutsField = objc.IBOutlet()
	_maxMoveField = objc.IBOutlet()
	_maxRotateField = objc.IBOutlet()
	
	def init( self ):
		"""
		Do all initializing here.
		"""
		NSBundle.loadNibNamed_owner_( "CutAndShakeDialog", self )
		random.seed()
		return self
	
	def interfaceVersion( self ):
		"""
		Distinguishes the API version the plugin was built for. 
		Return 1.
		"""
		return 1
	
	def title( self ):
		"""
		This is the human-readable name as it appears in the menu.
		"""
		try:
			return "Cut and Shake"
		except Exception as e:
			self.logToConsole( "title: %s" % str(e) )
	
	def actionName( self ):
		"""
		This is the title of the button in the settings dialog.
		"""
		try:
			return "Apply"
		except Exception as e:
			self.logToConsole( "actionName: %s" % str(e) )
	
	def keyEquivalent( self ):
		""" 
		The key together with Cmd+Shift will be the shortcut for the filter.
		Return None if you do not want to set a shortcut.
		Users can set their own shortcuts in System Prefs.
		"""
		try:
			return None
		except Exception as e:
			self.logToConsole( "keyEquivalent: %s" % str(e) )
	
	def setup(self):
		try:
			super( GlyphsFilterCutAndShake, self ).setup()
			FontMaster = self.valueForKey_( "fontMaster" )
		
			self.numberOfCuts = self.setDefaultIntegerValue( "numberOfCuts", 20, FontMaster )
			self.maxMove   = self.setDefaultFloatValue( "maxMove",  20.0, FontMaster )
			self.maxRotate = self.setDefaultFloatValue( "maxRotate", 8.0, FontMaster )
		
			self._numberOfCutsField.setIntegerValue_( self.numberOfCuts )
			self._maxMoveField.setFloatValue_( self.maxMove )
			self._maxRotateField.setFloatValue_( self.maxRotate )
		
			self.process_( None )
			return None # or if something goes wrong, a NSError object with details
		except Exception as e:
			self.logToConsole( "setup: %s" % str(e) )
	
	def setDefaultFloatValue( self, userDataKey, defaultValue, FontMaster ):
		"""Returns either the stored or default value for the given userDataKey."""
		if userDataKey in FontMaster.userData:
			return FontMaster.userData[userDataKey].floatValue()
		else:
			return defaultValue
			
	def setDefaultIntegerValue( self, userDataKey, defaultValue, FontMaster ):
		"""Returns either the stored or default value for the given userDataKey."""
		if userDataKey in FontMaster.userData:
			return FontMaster.userData[userDataKey].integerValue()
		else:
			return defaultValue
	
	@objc.IBAction
	def setNumberOfCutsValue_( self ,sender ):
		numberOfCuts = sender.floatValue()
		if numberOfCuts != self.numberOfCuts:
			self.numberOfCuts = numberOfCuts
			self.process_( None )

	@objc.IBAction
	def setMaxMoveValue_( self ,sender ):
		maxMove = sender.floatValue()
		if maxMove != self.maxMove:
			self.maxMove = maxMove
			self.process_( None )
			
	@objc.IBAction
	def setMaxRotateValue_( self ,sender ):
		maxRotate = sender.floatValue()
		if maxRotate != self.maxRotate:
			self.maxRotate = maxRotate
			self.process_( None )
	
	def processLayerWithValues( self, Layer, numberOfCuts, maxMove, maxRotate ):
		"""
		This is where your code for processing each layer goes.
		This method is the one eventually called by either the Custom Parameter or Dialog UI.
		"""
		try:
			self.randomCutLayer( Layer, numberOfCuts )
			self.randomMovePaths( Layer, abs(maxMove) )
			self.randomRotatePaths( Layer, abs(maxRotate) )
		except Exception as e:
			self.logToConsole( "processLayerWithValues: %s" % str(e) )
	
	def processFont_withArguments_( self, Font, Arguments ):
		"""
		Invoked when called as Custom Parameter in an instance at export.
		The Arguments come from the custom parameter in the instance settings. 
		The first item in Arguments is the class-name. After that, it depends on the filter.
		"""
		try:
			# Set default values for potential arguments (values), just in case:
			numberOfCuts = 10
			maxMove = 30.0
			maxRotate = 20.0
			
			# Override defaults with actual values from custom parameter:
			if len(Arguments) > 1:
				numberOfCuts = Arguments[1].integerValue()
				maxMove = Arguments[2].floatValue()
				maxRotate = Arguments[3].floatValue()
		
			# With these values, call our code on every glyph:
			FontMasterId = Font.fontMasterAtIndex_(0).id
			for Glyph in Font.glyphs:
				Layer = Glyph.layerForKey_( FontMasterId )
				self.processLayerWithValues( Layer, numberOfCuts, maxMove, maxRotate )
		except Exception as e:
			self.logToConsole( "processFont_withArguments_: %s" % str(e) )
	
	def process_( self, sender ):
		"""
		This method gets called when the filter is run with the dialog through the Filter menu.
		"""
		try:
			# Create Preview in Edit View, save and show original in ShadowLayer:
			ShadowLayers = self.valueForKey_( "shadowLayers" )
			Layers = self.valueForKey_( "layers" )
			checkSelection = True
			for k in range(len( ShadowLayers )):
				ShadowLayer = ShadowLayers[k]
				Layer = Layers[k]
				Layer.setPaths_( NSMutableArray.alloc().initWithArray_copyItems_( ShadowLayer.pyobjc_instanceMethods.paths(), True ) )
				Layer.setSelection_( NSMutableArray.array() )
				if len(ShadowLayer.selection()) > 0 and checkSelection:
					for i in range(len( ShadowLayer.paths )):
						currShadowPath = ShadowLayer.paths[i]
						currLayerPath = Layer.paths[i]
						for j in range(len(currShadowPath.nodes)):
							currShadowNode = currShadowPath.nodes[j]
							if ShadowLayer.selection().containsObject_( currShadowNode ):
								Layer.addSelection_( currLayerPath.nodes[j] )
				self.processLayerWithValues( Layer, self.numberOfCuts, self.maxMove, self.maxRotate )
			Layer.clearSelection()
		
			# Safe the values in the FontMaster. But could be saved in UserDefaults, too.
			FontMaster = self.valueForKey_( "fontMaster" )
			FontMaster.userData[ "numberOfCuts" ] = NSNumber.numberWithInteger_( self.numberOfCuts )
			FontMaster.userData[ "maxMove" ] = NSNumber.numberWithDouble_( self.maxMove )
			FontMaster.userData[ "maxRotate" ] = NSNumber.numberWithDouble_( self.maxRotate )
			
			# call the superclass to trigger the immediate redraw:
			super( GlyphsFilterCutAndShake, self ).process_( sender )
		except Exception as e:
			self.logToConsole( "process_: %s" % str(e) )
	
	def logToConsole( self, message ):
		"""
		The variable 'message' will be passed to Console.app.
		Use self.logToConsole( "bla bla" ) for debugging.
		"""
		myLog = "Filter %s:\n%s" % ( self.title(), message )
		NSLog( myLog )
		
	def rotationTransform( self, angle=180.0, x_orig=0.0, y_orig=0.0 ):
		"""Returns a TransformStruct for rotating."""
		try:
			RotationTransform = NSAffineTransform.transform()
			RotationTransform.translateXBy_yBy_( x_orig, y_orig )
			RotationTransform.rotateByDegrees_( angle )
			RotationTransform.translateXBy_yBy_( -x_orig, -y_orig )
			return RotationTransform
		except Exception as e:
			self.logToConsole( "rotationTransform: %s" % str(e) )

	def translateTransform( self, x_move=0.0, y_move=0.0 ):
		"""Returns a TransformStruct for translating."""
		try:
			TranslateTransform = NSAffineTransform.transform()
			TranslateTransform.translateXBy_yBy_( x_move, y_move )
			return TranslateTransform
		except Exception as e:
			self.logToConsole( "translateTransform: %s" % str(e) )

	def somewhereBetween( self, minimum, maximum ):
		try:
			precisionFactor = 100.0
			return random.randint( int( minimum * precisionFactor ), int( maximum * precisionFactor ) ) / precisionFactor
		except Exception as e:
			self.logToConsole( "somewhereBetween: %s" % str(e) )

	def rotate( self, x, y, angle=180.0, x_orig=0.0, y_orig=0.0):
		"""Rotates x/y around x_orig/y_orig by angle and returns result as [x,y]."""
		# TO DO: update this to use self.rotationTransform()
		try:
			new_angle = ( angle / 180.0 ) * math.pi
			new_x = ( x - x_orig ) * math.cos( new_angle ) - ( y - y_orig ) * math.sin( new_angle ) + x_orig
			new_y = ( x - x_orig ) * math.sin( new_angle ) + ( y - y_orig ) * math.cos( new_angle ) + y_orig
			return [ new_x, new_y ]
		except Exception as e:
			self.logToConsole( "rotate: %s" % str(e) )

	def rotatePath( self, thisPath, angle=180.0, x_orig=0.0, y_orig=0.0 ):
		"""Rotates a path around x_orig/y_orig by angle."""
		# TO DO: update this to use self.rotationTransform()
		try:
			for thisNode in thisPath.nodes:
				[ thisNode.x, thisNode.y ] = self.rotate( thisNode.x, thisNode.y, angle=(angle/1.0), x_orig=x_orig, y_orig=y_orig )
		except Exception as e:
			self.logToConsole( "rotatePath: %s" % str(e) )

	def translatePath( self, thisPath, translateByX=0.0, translateByY=0.0 ):
		"""Translates the path by translateByX/translateByY."""
		try:
			for thisNode in thisPath.nodes:
				thisNode.x += translateByX
				thisNode.y += translateByY
		except Exception as e:
			self.logToConsole( "translatePath: %s" % str(e) )

	def randomCutLayer( self, thisLayer, numberOfCuts ):
		try:
			lowestY = thisLayer.bounds.origin.y - self.goodMeasure
			highestY = thisLayer.bounds.origin.y + thisLayer.bounds.size.height + self.goodMeasure
			leftmostX = thisLayer.bounds.origin.x - self.goodMeasure
			rightmostX = thisLayer.bounds.origin.x + thisLayer.bounds.size.width + self.goodMeasure
			for i in range( numberOfCuts ):
				# make either horizontal or vertical cut:
				if random.randint( 0, 1 ) == 0:
					pointL = NSPoint( leftmostX,  self.somewhereBetween( lowestY, highestY ) )
					pointR = NSPoint( rightmostX, self.somewhereBetween( lowestY, highestY ) )
					thisLayer.cutBetweenPoints( pointL, pointR )
				else:
					pointB = NSPoint( self.somewhereBetween( leftmostX, rightmostX ), lowestY  )
					pointT = NSPoint( self.somewhereBetween( leftmostX, rightmostX ), highestY )
					thisLayer.cutBetweenPoints( pointB, pointT )
			return True
		except Exception as e:
			self.logToConsole( "randomCutLayer: %s" % str(e) )

	def randomMovePaths( self, thisLayer, maximumMove ):
		try:
			for thisPath in thisLayer.paths:
				xMove = self.somewhereBetween( -maximumMove/(2**0.5), maximumMove/(2**0.5) )
				yMove = self.somewhereBetween( -maximumMove/(2**0.5), maximumMove/(2**0.5) )
				self.translatePath( thisPath, translateByX=xMove, translateByY=yMove )
				#thisPath.transform = translateTransform( x_move=xMove, y_move=yMove )
			return True
		except Exception as e:
			self.logToConsole( "randomMovePaths: %s" % str(e) )
			return False

	def randomRotatePaths( self, thisLayer, maximumRotate ):
		try:
			for thisPath in thisLayer.paths:
				centerX = thisPath.bounds.origin.x + thisPath.bounds.size.width / 2.0
				centerY = thisPath.bounds.origin.y + thisPath.bounds.size.height / 2.0
				pathRotate = self.somewhereBetween( -maximumRotate, maximumRotate )
				self.rotatePath( thisPath, angle=pathRotate, x_orig=centerX, y_orig=centerY )
				# thisPath.transform = rotationTransform( angle=pathRotate, x_orig=centerX, y_orig=centerY )
			return True
		except Exception as e:
			self.logToConsole( "randomRotatePaths: %s" % str(e) )
			return False
	
