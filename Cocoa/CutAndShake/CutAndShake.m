//
//  CutAndShake.m
//  CutAndShake
//
//  Rainer Erich Scheichelbauer | mekkablue
//  Native Cocoa/ObjC version of the CutAndShake Glyphs filter plugin.
//
//  Cuts glyphs with random angled lines, then randomly moves and rotates
//  the resulting path fragments.
//

#import "CutAndShake.h"
#import <GlyphsCore/GSFont.h>
#import <GlyphsCore/GSFontMaster.h>
#import <GlyphsCore/GSGlyph.h>
#import <GlyphsCore/GSLayer.h>
#import <GlyphsCore/GSPath.h>
#import <GlyphsCore/GSNode.h>
#import <GlyphsCore/GSCallbackHandler.h>
#import <GlyphsCore/GSProxyShapes.h>
#import <objc/message.h>

// Declare the selector used via objc_msgSend to suppress -Wundeclared-selector
@interface NSObject (GlyphsToolOtherCutPaths)
+ (void)cutPathsInLayer:(id)layer forPoint:(NSPoint)p1 endPoint:(NSPoint)p2;
@end

// NSUserDefaults keys
static NSString *const kNumberOfCuts = @"com.mekkablue.CutAndShake.numberOfCuts";
static NSString *const kMaxMove      = @"com.mekkablue.CutAndShake.maxMove";
static NSString *const kMaxRotate    = @"com.mekkablue.CutAndShake.maxRotate";

// Extra margin around the glyph bounds when generating cut lines
static const CGFloat kGoodMeasure = 5.0;

@implementation CutAndShake

- (instancetype)init {
	self = [super init];
	return self;
}

#pragma mark - GSFilterPlugin required methods

- (NSUInteger)interfaceVersion {
	// Distinguishes the API version the plugin was built for.
	return 1;
}

- (NSString *)title {
	// Return the localised menu name.
	// Glyphs picks the best match for the current UI language.
	NSDictionary *names = @{
		@"en": @"Cut and Shake",
		@"de": @"Schneiden und schütteln",
		@"fr": @"Couper et secouer",
		@"es": @"Cortar y agitar",
		@"zh": @"🤺碎片化",
	};
	NSString *lang = [[[NSBundle mainBundle] preferredLocalizations] firstObject] ?: @"en";
	return names[lang] ?: names[@"en"];
}

- (NSString *)actionName {
	// The label of the Apply button in the filter dialog.
	NSDictionary *labels = @{
		@"en": @"Apply",
		@"de": @"Anwenden",
		@"fr": @"Appliquer",
		@"es": @"Aplicar",
		@"zh": @"应用",
	};
	NSString *lang = [[[NSBundle mainBundle] preferredLocalizations] firstObject] ?: @"en";
	return labels[lang] ?: labels[@"en"];
}

- (NSString *)keyEquivalent {
	// Return nil — no fixed keyboard shortcut (users set their own in System Settings).
	return nil;
}

#pragma mark - Dialog / View

- (NSView *)view {
	if (!_view) {
		[[NSBundle bundleForClass:[self class]]
			loadNibNamed:@"IBdialog"
			owner:self
			topLevelObjects:nil];
	}
	return _view;
}

- (NSError *)setup {
	// Called just before the dialog is shown.  Restore saved values and
	// push them into the text fields.
	[super setup];

	NSDictionary *defaults = @{
		kNumberOfCuts: @5,
		kMaxMove:      @50,
		kMaxRotate:    @20,
	};
	[[NSUserDefaults standardUserDefaults] registerDefaults:defaults];

	NSUserDefaults *ud = [NSUserDefaults standardUserDefaults];
	_numberOfCutsField.intValue   = (int)[ud integerForKey:kNumberOfCuts];
	_maxMoveField.floatValue      = [ud floatForKey:kMaxMove];
	_maxRotateField.floatValue    = [ud floatForKey:kMaxRotate];

	[_numberOfCutsField becomeFirstResponder];

	// Trigger an initial preview once the dialog is on screen.
	// Dispatching asynchronously ensures the edit view is ready to redraw.
	dispatch_async(dispatch_get_main_queue(), ^{
		[self process:nil];
	});
	return nil;
}

#pragma mark - IBActions

- (IBAction)setNumberOfCuts:(id)sender {
	[[NSUserDefaults standardUserDefaults]
		setInteger:[(NSTextField *)sender intValue]
		forKey:kNumberOfCuts];
	[self process:nil];
}

- (IBAction)setMaxMove:(id)sender {
	[[NSUserDefaults standardUserDefaults]
		setFloat:[(NSTextField *)sender floatValue]
		forKey:kMaxMove];
	[self process:nil];
}

- (IBAction)setMaxRotate:(id)sender {
	[[NSUserDefaults standardUserDefaults]
		setFloat:[(NSTextField *)sender floatValue]
		forKey:kMaxRotate];
	[self process:nil];
}

#pragma mark - process: (interactive / live preview)

/**
 Called each time the user changes a parameter in the dialog.
 Restores each working layer from the corresponding shadow layer
 (the frozen copy Glyphs made before the filter was first applied),
 then runs the filter, then hands control back to Glyphs via
 [super process:nil].
 */
- (void)process:(id)sender {
	NSUserDefaults *ud = [NSUserDefaults standardUserDefaults];
	NSInteger numberOfCuts = [ud integerForKey:kNumberOfCuts];
	CGFloat   maxMove      = [ud floatForKey:kMaxMove];
	CGFloat   maxRotate    = [ud floatForKey:kMaxRotate];

	for (NSUInteger k = 0; k < _shadowLayers.count; k++) {
		GSLayer *shadowLayer = _shadowLayers[k];
		GSLayer *layer       = _layers[k];

		// Restore to the pre-filter state from the shadow copy.
		layer.shapes    = [[NSMutableArray alloc] initWithArray:shadowLayer.shapes copyItems:YES];
		layer.selection = [NSMutableOrderedSet new];

		// Restore selection on individual nodes when the user works
		// in the Edit view with a sub-selection.
		if (shadowLayer.selection.count > 0 && _checkSelection) {
			for (NSUInteger i = 0; i < shadowLayer.shapes.count; i++) {
				GSPath *shadowPath = (GSPath *)[shadowLayer objectInShapesAtIndex:i];
				if (![shadowPath isKindOfClass:[GSPath class]]) continue;
				GSPath *layerPath = (GSPath *)[layer objectInShapesAtIndex:i];
				for (NSUInteger j = 0; j < shadowPath.nodes.count; j++) {
					GSNode *shadowNode = [shadowPath nodeAtIndex:j];
					if ([shadowLayer.selection containsObject:shadowNode]) {
						[layer addSelection:[layerPath nodeAtIndex:j]];
					}
				}
			}
		}

		[self applyFilterToLayer:layer
		           numberOfCuts:numberOfCuts
		                maxMove:maxMove
		              maxRotate:maxRotate];
		[layer clearSelection];
	}
	[super process:nil];
}

#pragma mark - Custom parameter string

- (NSString *)customParameterString {
	NSUserDefaults *ud = [NSUserDefaults standardUserDefaults];
	return [NSString stringWithFormat:@"%@; cuts:%ld; move:%.1f; rotate:%.1f",
		NSStringFromClass([self class]),
		(long)[ud integerForKey:kNumberOfCuts],
		[ud floatForKey:kMaxMove],
		[ud floatForKey:kMaxRotate]];
}

#pragma mark - Export / batch processing

- (void)processFont:(GSFont *)font withArguments:(NSArray *)arguments {
	// Called when the filter is invoked as a Custom Parameter at export.
	// arguments[0] is the class name; the remaining items are key:value pairs.

	NSInteger numberOfCuts = [[NSUserDefaults standardUserDefaults] integerForKey:kNumberOfCuts];
	CGFloat   maxMove      = [[NSUserDefaults standardUserDefaults] floatForKey:kMaxMove];
	CGFloat   maxRotate    = [[NSUserDefaults standardUserDefaults] floatForKey:kMaxRotate];

	// Parse key:value arguments supplied via the custom parameter.
	for (NSUInteger i = 1; i < arguments.count; i++) {
		NSString *arg = [arguments[i] stringByTrimmingCharactersInSet:
		                 [NSCharacterSet whitespaceCharacterSet]];
		NSArray  *kv  = [arg componentsSeparatedByString:@":"];
		if (kv.count != 2) continue;
		NSString *key   = [kv[0] stringByTrimmingCharactersInSet:
		                   [NSCharacterSet whitespaceCharacterSet]];
		NSString *value = [kv[1] stringByTrimmingCharactersInSet:
		                   [NSCharacterSet whitespaceCharacterSet]];
		if ([key isEqualToString:@"cuts"])   numberOfCuts = [value integerValue];
		if ([key isEqualToString:@"move"])   maxMove      = fabs([value floatValue]);
		if ([key isEqualToString:@"rotate"]) maxRotate    = fabs([value floatValue]);
	}

	// Iterate master layers using the SDK-template pattern (fontMasterAtIndex: +
	// layerForKey:) rather than glyph.layers enumeration, which avoids issues
	// with Glyphs' custom ordered-dictionary collection during export.
	_checkSelection = NO;
	for (NSUInteger mi = 0; mi < 64; mi++) {
		GSFontMaster *master = [font fontMasterAtIndex:mi];
		if (!master) break;
		NSString *masterId = [master valueForKey:@"id"];
		if (!masterId) continue;
		for (GSGlyph *glyph in font.glyphs) {
			GSLayer *layer = [glyph layerForKey:masterId];
			if (!layer) continue;
			[self applyFilterToLayer:layer
			           numberOfCuts:numberOfCuts
			                maxMove:maxMove
			              maxRotate:maxRotate];
		}
	}
}

#pragma mark - Core filter logic

/**
 Apply the full CutAndShake effect to a single @p layer.
 1. Make @p numberOfCuts random angled cuts.
 2. Shift each resulting path fragment by a random vector ≤ @p maxMove.
 3. Rotate each path fragment around its own centre by ≤ @p maxRotate degrees.
 */
- (void)applyFilterToLayer:(GSLayer *)layer
             numberOfCuts:(NSInteger)numberOfCuts
                  maxMove:(CGFloat)maxMove
                maxRotate:(CGFloat)maxRotate {

	[self randomCutLayer:layer numberOfCuts:numberOfCuts];
	[self randomMovePaths:layer    maxMove:maxMove];
	[self randomRotatePaths:layer  maxRotate:maxRotate];
}

/**
 Make @p numberOfCuts random angled cuts through @p layer.
 Each cut either spans left-to-right or top-to-bottom; both endpoints get
 independently-random positions, producing diagonal cuts (matching the Python
 version).  The cut lines extend @c kGoodMeasure beyond the layer bounds so
 they cleanly intersect all paths.
 */
- (void)randomCutLayer:(GSLayer *)layer numberOfCuts:(NSInteger)numberOfCuts {
	NSRect b = layer.bounds;
	CGFloat lowestY    = NSMinY(b) - kGoodMeasure;
	CGFloat highestY   = NSMaxY(b) + kGoodMeasure;
	CGFloat leftmostX  = NSMinX(b) - kGoodMeasure;
	CGFloat rightmostX = NSMaxX(b) + kGoodMeasure;

	// layer.cutBetweenPoints() in the Python API is a wrapper around
	// +[GlyphsToolOther cutPathsInLayer:forPoint:endPoint:].
	// We look up the class at runtime so we don't need its header.
	Class GlyphsToolOther = NSClassFromString(@"GlyphsToolOther");

	for (NSInteger i = 0; i < numberOfCuts; i++) {
		NSPoint p1, p2;
		if (arc4random_uniform(2) == 0) {
			// Roughly horizontal cut: spans left-to-right, both Y values independent → angled
			p1 = NSMakePoint(leftmostX,  [self randomBetween:lowestY and:highestY]);
			p2 = NSMakePoint(rightmostX, [self randomBetween:lowestY and:highestY]);
		} else {
			// Roughly vertical cut: spans top-to-bottom, both X values independent → angled
			p1 = NSMakePoint([self randomBetween:leftmostX and:rightmostX], lowestY);
			p2 = NSMakePoint([self randomBetween:leftmostX and:rightmostX], highestY);
		}
		((void (*)(id, SEL, id, NSPoint, NSPoint))objc_msgSend)(
			(id)GlyphsToolOther,
			@selector(cutPathsInLayer:forPoint:endPoint:),
			layer, p1, p2);
	}
}

/**
 Translate each path in @p layer by a random vector whose magnitude
 is at most @p maxMove (distributed uniformly per axis up to maxMove/√2
 so the maximum distance equals @p maxMove).

 GSPath has no native -applyTransform: in ObjC; the Python wrapper
 achieves the same effect by iterating every GSNode and transforming
 its position.  We do the same here using KVC (Cocoa wraps NSPoint
 in NSValue automatically).
 */
- (void)randomMovePaths:(GSLayer *)layer maxMove:(CGFloat)maxMove {
	CGFloat halfRange = maxMove / sqrt(2.0);
	for (id path in layer.paths) {
		CGFloat dx = [self randomBetween:-halfRange and:halfRange];
		CGFloat dy = [self randomBetween:-halfRange and:halfRange];
		NSAffineTransform *t = [NSAffineTransform transform];
		[t translateXBy:dx yBy:dy];
		[self applyTransform:t toNodesOfPath:path];
	}
}

/**
 Rotate each path in @p layer by a random angle in [−maxRotate, +maxRotate]
 degrees around the path's own bounding-box centre.
 */
- (void)randomRotatePaths:(GSLayer *)layer maxRotate:(CGFloat)maxRotate {
	for (id path in layer.paths) {
		NSRect  b       = [[path valueForKey:@"bounds"] rectValue];
		CGFloat cx      = NSMidX(b);
		CGFloat cy      = NSMidY(b);
		CGFloat degrees = [self randomBetween:-maxRotate and:maxRotate];

		NSAffineTransform *t = [NSAffineTransform transform];
		[t translateXBy:cx yBy:cy];
		[t rotateByDegrees:degrees];
		[t translateXBy:-cx yBy:-cy];
		[self applyTransform:t toNodesOfPath:path];
	}
}

/**
 Apply @p transform to every node in @p path by reading and writing
 each node's @c position via KVC.  Cocoa automatically wraps and
 unwraps NSPoint values as NSValue when accessed through KVC.
 This mirrors what the Python wrapper's GSPath.applyTransform() does.
 */
- (void)applyTransform:(NSAffineTransform *)transform toNodesOfPath:(id)path {
	for (id node in [path valueForKey:@"nodes"]) {
		NSPoint pos    = [[node valueForKey:@"position"] pointValue];
		NSPoint newPos = [transform transformPoint:pos];
		[node setValue:[NSValue valueWithPoint:newPos] forKey:@"position"];
	}
}

#pragma mark - Helpers

/** Return a uniform random CGFloat in [minimum, maximum]. */
- (CGFloat)randomBetween:(CGFloat)minimum and:(CGFloat)maximum {
	CGFloat range  = maximum - minimum;
	CGFloat random = (CGFloat)arc4random() / (CGFloat)UINT32_MAX;
	return minimum + random * range;
}

@end
