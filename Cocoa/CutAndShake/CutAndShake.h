//
//  CutAndShake.h
//  CutAndShake
//
//  Rainer Erich Scheichelbauer | mekkablue
//  Native Cocoa/ObjC version of the CutAndShake Glyphs filter plugin.
//

#import <Cocoa/Cocoa.h>
// In Glyphs 4, GSFilterPlugin lives in the GlyphsApp framework.
// (In Glyphs 3 it used to be <GlyphsCore/GSFilterPlugin.h>.)
#import <GlyphsApp/GSFilterPlugin.h>

@interface CutAndShake : GSFilterPlugin

// IBOutlets for the dialog fields
@property (nonatomic, assign) IBOutlet NSTextField *numberOfCutsField;
@property (nonatomic, assign) IBOutlet NSTextField *maxMoveField;
@property (nonatomic, assign) IBOutlet NSTextField *maxRotateField;

// IBActions triggered by the dialog fields
- (IBAction)setNumberOfCuts:(id)sender;
- (IBAction)setMaxMove:(id)sender;
- (IBAction)setMaxRotate:(id)sender;

@end
