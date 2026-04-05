import { useState, useEffect } from 'react';
import { Pressable, Image, StyleSheet, Linking } from 'react-native';

const BACKEND_URL = 'http://localhost:8000'; // TODO: replace with real backend URL

export default function MasterAgentFAB() {
  const [agentAddress, setAgentAddress] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${BACKEND_URL}/config`)
      .then((res) => res.json())
      .then((data) => {
        if (data.resale_copilot_agent_address) {
          setAgentAddress(data.resale_copilot_agent_address);
        }
      })
      .catch(() => {
        // Backend unavailable — hide button
      });
  }, []);

  if (!agentAddress) return null;

  const handlePress = () => {
    Linking.openURL(`https://asi1.ai/chat?agent=${agentAddress}`);
  };

  return (
    <Pressable
      onPress={handlePress}
      accessibilityLabel="Chat with AI agent on ASI:One"
      accessibilityRole="button"
      style={({ pressed }) => [styles.fab, pressed && styles.fabPressed]}
    >
      <Image
        source={require('../assets/asi-one-logo-modified.png')}
        style={styles.icon}
        resizeMode="contain"
      />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  fab: {
    position: 'absolute',
    bottom: 24,
    right: 16,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#7C3AED',
    alignItems: 'center',
    justifyContent: 'center',
    elevation: 6,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    zIndex: 999,
  },
  fabPressed: {
    opacity: 0.8,
    transform: [{ scale: 0.95 }],
  },
  icon: {
    width: 30,
    height: 30,
    tintColor: '#FFFFFF',
  },
});
