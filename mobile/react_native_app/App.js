import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { View, Text, StyleSheet } from 'react-native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';

import { DashboardScreen } from './src/screens/DashboardScreen';
import { ReportScreen } from './src/screens/ReportScreen';
import { ControlScreen } from './src/screens/ControlScreen';
import { COLORS } from './src/styles/theme';

const Tab = createBottomTabNavigator();

export default function App() {
  return (
    <NavigationContainer>
      <Tab.Navigator
        screenOptions={({ route }) => ({
          headerShown: false,
          tabBarIcon: ({ color, size }) => {
            let iconName;

            if (route.name === 'Dashboard') {
              iconName = 'chart-line';
            } else if (route.name === 'Report') {
              iconName = 'file-document';
            } else if (route.name === 'Control') {
              iconName = 'cog';
            }

            return <Icon name={iconName} size={size} color={color} />;
          },
          tabBarActiveTintColor: COLORS.cyan,
          tabBarInactiveTintColor: COLORS.textMuted,
          tabBarStyle: {
            backgroundColor: COLORS.darkBg,
            borderTopColor: COLORS.border,
            borderTopWidth: 1,
            paddingBottom: 8,
            paddingTop: 8,
          },
          tabBarLabel: ({ color, children }) => (
            <View style={styles.labelContainer}>
              <Text style={[styles.label, { color }]}>{children}</Text>
            </View>
          ),
        })}
      >
        <Tab.Screen
          name="Dashboard"
          component={DashboardScreen}
          options={{
            tabBarLabel: 'Dashboard',
          }}
        />
        <Tab.Screen
          name="Report"
          component={ReportScreen}
          options={{
            tabBarLabel: 'Report',
          }}
        />
        <Tab.Screen
          name="Control"
          component={ControlScreen}
          options={{
            tabBarLabel: 'Control',
          }}
        />
      </Tab.Navigator>
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  labelContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 4,
  },
  label: {
    fontSize: 10,
    fontWeight: '500',
  },
});
