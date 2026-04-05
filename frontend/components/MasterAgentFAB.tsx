import { TouchableOpacity, Image, View, StyleSheet, Linking } from 'react-native';

const FALLBACK_AGENT_ADDRESS = 'agent1q_placeholder'; // TODO: replace with real agent address
const BACKEND_URL = 'http://localhost:8000'; // TODO: replace with real backend URL

export default function MasterAgentFAB() {
  const handlePress = () => {
    fetch(`${BACKEND_URL}/config`)
      .then((res) => res.json())
      .then((data) => {
        const address = data.resale_copilot_agent_address || FALLBACK_AGENT_ADDRESS;
        Linking.openURL(`https://asi1.ai/chat?agent=${address}`);
      })
      .catch(() => {
        Linking.openURL(`https://asi1.ai/chat?agent=${FALLBACK_AGENT_ADDRESS}`);
      });
  };

  return (
    <TouchableOpacity
      style={styles.fab}
      activeOpacity={0.8}
      onPress={handlePress}
      accessibilityLabel="Chat with AI agent on ASI:One"
    >
      <View style={styles.whiteLayer} />
      <Image
        source={require('../assets/asi-one-logo-modified.png')}
        style={styles.icon}
        resizeMode="contain"
      />
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  fab: {
    position: 'absolute',
    bottom: 36,
    right: 20,
    width: 84,
    height: 84,
    borderRadius: 42,
    backgroundColor: '#FFFFFF',
    alignItems: 'center',
    justifyContent: 'center',
    elevation: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.35,
    shadowRadius: 8,
  },
  whiteLayer: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: '#FFFFFF',
    borderRadius: 42,
    overflow: 'hidden',
  },
  icon: {
    width: 72,
    height: 72,
  },
});
