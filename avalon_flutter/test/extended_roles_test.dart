import 'package:avalon_flutter/features/game/presentation/screens/role_reveal_screen.dart';
import 'package:avalon_flutter/features/setup/presentation/controllers/setup_controller.dart';
import 'package:avalon_flutter/features/setup/presentation/setup_screen.dart';
import 'package:avalon_flutter/features/game/domain/models/role.dart';
import 'package:avalon_flutter/features/game/domain/models/player.dart';
import 'package:avalon_flutter/features/game/domain/models/game_state.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

// Helper to access state for verification
final stateContainer = ProviderContainer();

void main() {
  testWidgets('Extended Roles: 9 Player Recommendation & Tristan/Iseult', (WidgetTester tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(
          home: SetupScreen(),
        ),
      ),
    );
    await tester.pumpAndSettle();

    // 1. Add 9 Players
    final nameInput = find.byType(TextField);
    final addButton = find.byIcon(Icons.add);

    for (int i = 1; i <= 9; i++) {
        await tester.enterText(nameInput, 'Player$i');
        await tester.tap(addButton);
        await tester.pumpAndSettle();
    }

    // 2. Tap "Recommended" Button
    print('DEBUG: Added 9 players. Taping Recommended.');
    
    // It might be below the keyboard or off screen? 
    // Close keyboard just in case
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pumpAndSettle();

    final recommendButton = find.text('Recommended');
    // Check if found
    expect(recommendButton, findsOneWidget, reason: "Recommended button not found");
    
    await tester.ensureVisible(recommendButton);
    await tester.tap(recommendButton);
    await tester.pumpAndSettle();

    // 3. Start Game
    print('DEBUG: Starting Game.');
    final startButton = find.text('EMPEZAR JUEGO');
    await tester.ensureVisible(startButton);
    await tester.tap(startButton);
    await tester.pumpAndSettle();

    // 4. Verify we are in Role Reveal
    expect(find.byType(RoleRevealScreen), findsOneWidget);

    // 5. Check Cycle
    bool foundTristanMsg = false;
    bool foundIseultMsg = false;

    for (int i = 0; i < 9; i++) {
        // Reveal
        final revealButton = find.text('REVELAR ROL');
        await tester.tap(revealButton);
        await tester.pumpAndSettle();

        // Check text
        if (findsText('Tu amada Isolda:')) {
            print('DEBUG: Found Tristan viewing Isolda');
            foundTristanMsg = true;
        }
        if (findsText('Tu amado Tristán:')) {
             print('DEBUG: Found Iseult viewing Tristan');
             foundIseultMsg = true;
        }

        // Next
        final nextButton = find.widgetWithText(ElevatedButton, (i == 8) ? "EMPEZAR JUEGO" : "SIGUIENTE JUGADOR");
        await tester.tap(nextButton);
        await tester.pumpAndSettle();
    }

    expect(foundTristanMsg, isTrue, reason: "Tristan logic failed");
    expect(foundIseultMsg, isTrue, reason: "Iseult logic failed");

  });
}

bool findsText(String text) {
  try {
    find.text(text).evaluate().first;
    return true;
  } catch (e) {
    return false;
  }
}
