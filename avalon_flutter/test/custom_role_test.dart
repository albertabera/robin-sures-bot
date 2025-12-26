import 'package:avalon_flutter/features/game/presentation/screens/role_reveal_screen.dart';
import 'package:avalon_flutter/features/setup/presentation/controllers/setup_controller.dart';
import 'package:avalon_flutter/features/setup/presentation/setup_screen.dart';
import 'package:avalon_flutter/features/game/domain/models/role.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('Custom Role Selection Flow Test', (WidgetTester tester) async {
    // 1. Pump the SetupScreen wrapped in ProviderScope
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(
          home: SetupScreen(),
        ),
      ),
    );
    await tester.pumpAndSettle(); // Wait for FadeInDown animations

    // Verify Title
    expect(find.text('Avalon'), findsOneWidget);

    // 2. Add 5 Players to satisfy requirements
    final names = ['Alice', 'Bob', 'Charlie', 'Dave', 'Eve'];
    final nameInput = find.byType(TextField);
    final addButton = find.byIcon(Icons.add);

    for (final name in names) {
      await tester.enterText(nameInput, name);
      await tester.tap(addButton);
      await tester.pumpAndSettle(); // Allow list animation
    }

    // 3. Toggle Custom Roles
    // Find Merlin and Morgana chips
    final merlinChip = find.widgetWithText(FilterChip, 'Merlin');
    final morganaChip = find.widgetWithText(FilterChip, 'Morgana');
    
    // Ensure they are visible (horizontal list might need scrolling)
    await tester.ensureVisible(merlinChip);
    await tester.tap(merlinChip);
    await tester.pump();

    await tester.ensureVisible(morganaChip);
    await tester.tap(morganaChip);
    await tester.pump();

    // 4. Start Game
    final startButton = find.text('EMPEZAR JUEGO');
    // It should be visible now that we have 5 players
    await tester.ensureVisible(startButton);
    await tester.tap(startButton);
    
    // 5. Verify Navigation
    await tester.pumpAndSettle(); // Wait for navigation transition
    
    expect(find.byType(RoleRevealScreen), findsOneWidget);
    expect(find.text("Pasa el dispositivo a:"), findsOneWidget);
  });
}
